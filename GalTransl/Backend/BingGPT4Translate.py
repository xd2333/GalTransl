import json
import random
import time
import asyncio
import traceback
import zhconv
from sys import exit

from EdgeGPT import Chatbot, ConversationStyle
from GalTransl import LOGGER
from GalTransl.ConfigHelper import CProjectConfig, initProxyList, randSelectInList
from GalTransl.Cache import get_transCache_from_json, save_transCache_to_json
from GalTransl.CSentense import CTransList, CSentense
from GalTransl.Dictionary import CGptDict

TRANS_PROMPT = """Generate content for translating the input and output as required.#no_search
# On Input
The last line is a fragment of a Japanese visual novel script in key-value objects list json format.
# On Translating Steps:
Process the objects one by one, step by step:
1. If the `id` is incrementing, first reasoning the context for sort out the subject/object relationship and choose the polysemy wording that best fits the plot and common sense to retain the original meaning as faithful as possible.
2. For the sentence, depending on the `name` of current object:
Treat as dialogue if name in object, should use highly lifelike words, use highly colloquial and Native-Chinese language and keep the original speech style.
Treat as monologue/narrator if no name key, should be translated from the character's self-perspective, omitting personal/possessive pronouns as closely as the original.
3. Translate Japanese to Simplified Chinese word by word, keep same use of punctuation, linebreak(\\r\\n) and spacing as the original text.The translation should be faithful, fluent, no missing words.
Ensure that the content of different objects are decoupled.Then move to the next object.
# On Output:
Your output start with "Transl:", then write the result json with same id and name,
in each object, remove `src` and add `dst` for translation result, add `"conf": <0-1.00>` for assessing translation confidence,
if conf <= 0.94, add `"doub": <list>` to store doubtful content,
if found unknown proper noun, add `"unkn": <list>` to store.
All in one line without any explanation or comments, then end.
[Glossary]
Input:
[Input]"""

PROOFREAD_PROMPT = """Generate content for proofreading the input and output as required.#no_search
# On Input
The last line is a Japanese visual novel script fragment json objects list, each object is a sentence with follow keys:`id`, `name`, `src(original jp text)`, `dst(preliminary zh-cn translation)`.
# On Proofreading requirements for each object
[Rules]
* Treat as dialogue if name in object, treat as monologue/narrator if no name key.
* The glossary (if provided) should be referred to before proofreading.
* Keep same use of punctuation and line break symbols(\\r\\n) as the correspond original text.
* When polishing, compared to the correspond original text, avoid adding content or name that is redundant, inconsistent or fictitious.
[Goals]
* Completeness
Contrast the dst with the src, remove extraneous content and complete missing translations in the dst.
* Contextual correctness
Reasoning about the plot based on src and name in the order of id, correct potential bugs in dst such as wrong pronouns use, wrong logic, wrong wording, etc.
* Polishing
Properly adjust the word order and polish the wording of the inline sentence to make dst more fluent, expressive and in line with Chinese reading habits.
# On Output
Start with a short basic summary like `Rivised id <id>, for <goals and rules>; id <id2>,...`.
Then write "Result:",
write the whole result json objects list in a json block(```json),
copy the `id` and `name`(if have) directly, 
remove origin `src` and `dst`, replace by `newdst` for zh-cn proofreading result, all in one line, then end.
[Glossary]
Input:
[Input]"""


class CBingGPT4Translate:
    def __init__(self, config: CProjectConfig, cookiefile_list: list[str]):
        LOGGER.info("NewBing transl-api version:0.8 [2023.05.20]")
        if config.getKey("internals.enableProxy") == True:
            self.proxies = initProxyList(config)
        else:
            self.proxies = None
            LOGGER.warning("不使用代理")

        self.cookiefile_list = cookiefile_list
        self.current_cookie_file = ""
        self.throttled_cookie_list = []
        self.proxy = randSelectInList(self.proxies)["addr"] if self.proxies else None
        self.request_count = 0
        self.sleep_time = 0
        self.last_file_name = ""
        self.chatbot = Chatbot(cookies=self.get_random_cookie(), proxy=self.proxy)

    async def translate(self, trans_list: CTransList, dict="", proofread=False):
        prompt_req = TRANS_PROMPT if not proofread else PROOFREAD_PROMPT
        input_list = []
        for i, trans in enumerate(trans_list):
            # [{"no":xx,"name":"xx","content":"xx"}]
            if not proofread:
                tmp_obj = {
                    "id": trans.index,
                    "name": trans.speaker,
                    "src": trans.post_jp,
                }
                if trans.speaker == "":
                    del tmp_obj["name"]
                input_list.append(tmp_obj)
            else:
                tmp_obj = {
                    "id": trans.index,
                    "name": trans.speaker,
                    "src": trans.post_jp,
                    "dst": trans.pre_zh
                    if trans.proofread_zh == ""
                    else trans.proofread_zh,
                }
                if trans.speaker == "":
                    del tmp_obj["name"]

                input_list.append(tmp_obj)
        input_json = json.dumps(input_list, ensure_ascii=False)
        prompt_req = prompt_req.replace("[Input]", input_json)
        prompt_req = prompt_req.replace("[Glossary]", dict)
        LOGGER.info(f"->{'翻译输入' if not proofread else '校对输入'}：{dict}\n{input_json}\n")
        while True:  # 一直循环，直到得到数据
            try:
                self.request_count += 1
                LOGGER.info("->请求次数：" + str(self.request_count) + "\n")
                resp = await self.chatbot.ask(
                    prompt=prompt_req, conversation_style=ConversationStyle.creative
                )
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                LOGGER.info("Error:%s, Please wait 30 seconds" % ex)
                traceback.print_exc()
                await asyncio.sleep(5)
                continue
            # LOGGER.info("->输出：" + str(resp) + "\n")
            if "Request is throttled." in str(resp):
                LOGGER.info("->Request is throttled.")
                self.throttled_cookie_list.append(self.current_cookie_file)
                self.cookiefile_list.remove(self.current_cookie_file)
                await asyncio.sleep(self.sleep_time)
                self.chatbot = Chatbot(
                    cookies=self.get_random_cookie(), proxy=self.proxy
                )
                await self.chatbot.reset()
                continue

            if "New topic" in str(resp):
                LOGGER.info("->Need New topic")
                await self.chatbot.reset()
                continue

            if (
                "messages" not in resp["item"]
                or len(resp["item"]["messages"]) < 2
                or "text" not in resp["item"]["messages"][1]
                or "[{" not in resp["item"]["messages"][1]["text"]
            ):
                for tran in trans_list:
                    if not proofread:
                        tran.pre_zh = "Failed translation"
                        tran.post_zh = "Failed translation"
                        tran.trans_by = "NewBing(Failed)"
                    else:
                        tran.proofread_zh = tran.post_zh
                        tran.proofread_by = "NewBing(Failed)"
                LOGGER.info("->NewBing大小姐拒绝了本次请求🙏\n")
                # 换一个cookie
                self.chatbot = Chatbot(
                    cookies=self.get_random_cookie(), proxy=self.proxy
                )
                return trans_list

            result_text = resp["item"]["messages"][1]["text"]
            LOGGER.info("->输出：\n" + result_text + "\n")
            result_text = result_text[
                result_text.find("[{") : result_text.rfind("}]") + 2
            ].strip()
            result_text = result_text.replace("\r", "\\r").replace(
                "\n", "\\n"
            )  # 防止json解析错误
            # 修复丢冒号
            result_text = (
                result_text.replace(", src:", ', "src":')
                .replace(", dst:", ', "dst":')
                .replace(", doub:", ', "doub":')
                .replace(", conf:", ', "conf":')
                .replace(", unkn:", ', "unkn":')
                .replace("},\\n{", "},{")
            )
            try:
                result_json = json.loads(result_text)  # 尝试解析json
            except:
                LOGGER.info("->非json：\n" + result_text + "\n")
                traceback.print_exc()
                await asyncio.sleep(2)
                await self.chatbot.reset()
                continue

            if len(result_json) != len(input_list):
                LOGGER.info("->错误的输出行数：\n" + result_text + "\n")
                await asyncio.sleep(2)
                await self.chatbot.reset()
                continue
            key_name = "dst" if not proofread else "newdst"
            have_error = False
            for i, result in enumerate(result_json):
                if key_name not in result:
                    LOGGER.info("->缺少输出：\n" + result_text + "\n")
                    have_error = True
                    break
                if trans_list[i].post_jp != "" and result[key_name] == "":  # 本行输出不应为空
                    LOGGER.info("->空白输出：\n" + result_text + "\n")
                    have_error = True
                    break
                if (
                    ("(" in result[key_name] and "（" not in trans_list[i].post_jp)
                    or ("（" in result[key_name] and "（" not in trans_list[i].post_jp)
                    or (
                        "*" in result[key_name]
                        or "<" in result[key_name]
                        or "“" == result[key_name][0]
                        or "”" == result[key_name][-1]
                    )
                    or ("/" in result[key_name] and "/" not in trans_list[i].post_jp)
                ):
                    LOGGER.info("->多余符号：\n" + result_text + "\n")
                    result[key_name] = self.remove_extra_pronouns(result[key_name])
                    await self.chatbot.reset()
                # 修复输出中的换行符
                if "\r\n" not in result[key_name] and "\n" in result[key_name]:
                    result[key_name] = result[key_name].replace("\n", "\r\n")
                if result[key_name].startswith("\r\n") and not trans_list[
                    i
                ].post_jp.startswith("\r\n"):
                    result[key_name] = result[key_name][2:]
                result[key_name] = zhconv.convert(result[key_name], "zh-cn")  # 防止出现繁体
                if not proofread:
                    trans_list[i].pre_zh = result[key_name]
                    trans_list[i].post_zh = result[key_name]
                    trans_list[i].trans_by = "NewBing"
                    if "conf" in result:
                        trans_list[i].trans_conf = result["conf"]
                    if "doub" in result:
                        trans_list[i].doub_content = result["doub"]
                    if "unkn" in result:
                        trans_list[i].unknown_proper_noun = result["unkn"]
                else:
                    trans_list[i].proofread_zh = result[key_name]
                    trans_list[i].proofread_by = "NewBing"

            if have_error:
                await asyncio.sleep(2)
                await self.chatbot.reset()
                continue

            break
        return trans_list

    async def batch_translate(
        self,
        filename,
        cache_file_path,
        trans_list: CTransList,
        num_pre_request: int,
        chatgpt_dict: CGptDict = None,
        retry_failed: bool = False,
        proofread: bool = False,
    ) -> CTransList:
        """批量翻译

        Args:
            filename (str): 文件名
            cache_file_path (_type_): 缓存文件路径
            trans_list (CTransList): translate列表
            num_pre_request (int): 每次请求的数量
            chatgpt_dict (ChatgptDict, optional): _description_. Defaults to None.
            proofread (bool, optional): _description_. Defaults to False.

        Returns:
            CTransList: _description_
        """

        _, trans_list_unhit = get_transCache_from_json(
            trans_list, cache_file_path, retry_failed=retry_failed, proofread=proofread
        )
        if len(trans_list_unhit) == 0:
            return []
        # 新文件重置chatbot
        if self.last_file_name != "" and self.last_file_name != filename:
            self.chatbot.reset()
            self.last_file_name = filename

        i = 0
        trans_result_list = []
        len_trans_list = len(trans_list_unhit)
        while i < len_trans_list:
            await asyncio.sleep(1)
            trans_list_split = (
                trans_list_unhit[i : i + num_pre_request]
                if (i + num_pre_request < len_trans_list)
                else trans_list_unhit[i:]
            )

            # 生成dic prompt
            if chatgpt_dict != None:
                dic_prompt = chatgpt_dict.gen_prompt(trans_list_split)
            else:
                dic_prompt = ""

            trans_result = await self.translate(
                trans_list_split, dic_prompt, proofread=proofread
            )

            i += num_pre_request
            for trans in trans_result:
                LOGGER.info(trans)
            trans_result_list += trans_result
            save_transCache_to_json(trans_list, cache_file_path, proofread=proofread)
            LOGGER.info(
                f"{filename}：{str(len(trans_result_list))}/{str(len_trans_list)}"
            )

        return trans_result_list

    def reset_conversation(self):
        self.chatbot.reset_conversation()

    def remove_extra_pronouns(self, text):
        return (
            text.replace("**", "").replace("(我)", "").replace("“", "").replace("”", "")
        )

    def get_random_cookie(self):
        if len(self.cookiefile_list) == 0 and len(self.throttled_cookie_list) == 0:
            return None

        if len(self.cookiefile_list) == 0:
            self.cookiefile_list = self.throttled_cookie_list
            self.throttled_cookie_list = []
            self.sleep_time = 600
        self.current_cookie_file = random.choice(self.cookiefile_list)
        LOGGER.info(f"当前使用cookie文件：{self.current_cookie_file}")
        cookies = json.loads(open(self.current_cookie_file, encoding="utf-8").read())
        return cookies
