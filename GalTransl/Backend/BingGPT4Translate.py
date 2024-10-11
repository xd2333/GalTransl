import json
import random
import sys
import time
import asyncio
import traceback
from sys import exit

from opencc import OpenCC
from typing import Optional
from re_edge_gpt import Chatbot, ConversationStyle
from GalTransl import LOGGER, LANG_SUPPORTED
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.Cache import get_transCache_from_json_new, save_transCache_to_json
from GalTransl.CSentense import CTransList, CSentense
from GalTransl.Dictionary import CGptDict
from GalTransl.Utils import extract_code_blocks
from GalTransl.Backend.Prompts import (
    NewBing_CONF_PROMPT,
    NewBing_FORCE_PROMPT,
    NewBing_NAME_PROMPT3,
    NewBing_PROOFREAD_PROMPT,
    NewBing_TRANS_PROMPT,
    H_WORDS_LIST
)


class CBingGPT4Translate:
    def __init__(
        self,
        config: CProjectConfig,
        cookiefile_list: list[str],
        proxyPool: Optional[CProxyPool],
    ):
        # 保存间隔
        if val := config.getKey("save_steps"):
            self.save_steps = val
        else:
            self.save_steps = 1
        # 语言设置
        if val := config.getKey("language"):
            sp = val.split("2")
            self.source_lang = sp[0]
            self.target_lang = sp[1]
        elif val := config.getKey("sourceLanguage"):  # 兼容旧版本配置
            self.source_lang = val
            self.target_lang = config.getKey("targetLanguage")
        else:
            self.source_lang = "ja"
            self.target_lang = "zh-cn"
        if self.source_lang not in LANG_SUPPORTED.keys():
            raise ValueError("错误的源语言代码：" + self.source_lang)
        else:
            self.source_lang = LANG_SUPPORTED[self.source_lang]
        if self.target_lang not in LANG_SUPPORTED.keys():
            raise ValueError("错误的目标语言代码：" + self.target_lang)
        else:
            self.target_lang = LANG_SUPPORTED[self.target_lang]

        if config.getKey("internals.enableProxy") == True:
            self.proxyProvider = proxyPool
        else:
            self.proxyProvider = None
            
        if val := config.getKey("gpt.forceNewBingHs"):
            self.force_NewBing_hs_mode = val
        else:
            self.force_NewBing_hs_mode = False
        # 跳过h
        if val := config.getKey("skipH"):
            self.skipH = val
        else:
            self.skipH = False
        # 跳过重试
        if val := config.getKey("skipRetry"):
            self.skipRetry = val
        else:
            self.skipRetry = False
        # 记录确信度
        if val := config.getKey("gpt.recordConfidence"):
            self.record_confidence = val
        else:
            self.record_confidence = False
        # 流式输出模式
        if val := config.getKey("gpt.streamOutputMode"):
            self.streamOutputMode = val
        else:
            self.streamOutputMode = False

        self.cookiefile_list = cookiefile_list
        self.current_cookie_file = ""
        self.throttled_cookie_list = []
        self.proxy = self.proxyProvider.getProxy().addr if self.proxyProvider else None
        self.request_count = 0
        self.sleep_time = 0
        self.last_file_name = ""

        if self.target_lang == "Simplified_Chinese":
            self.opencc = OpenCC("t2s.json")
        elif self.target_lang == "Traditional_Chinese":
            self.opencc = OpenCC("s2tw.json")

        self.init_chatbot()
            
    def init_chatbot(self):
        while True:
            try:
                self.chatbot = Chatbot(
                    proxy=self.proxy, cookies=self.get_random_cookie()
                )
                break
            except Exception as e:
                LOGGER.info(f"换cookie失败：{e}")
                asyncio.sleep(1)
                continue

    async def translate(self, trans_list: CTransList, gptdict="", proofread=False):
        prompt_req = NewBing_TRANS_PROMPT if not proofread else NewBing_PROOFREAD_PROMPT
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
        input_json = ""
        # dump as jsonline
        for obj in input_list:
            input_json += json.dumps(obj, ensure_ascii=False) + "\n"

        prompt_req = prompt_req.replace("[Input]", input_json)
        prompt_req = prompt_req.replace("[Glossary]", gptdict)
        prompt_req = prompt_req.replace("[SourceLang]", self.source_lang)
        prompt_req = prompt_req.replace("[TargetLang]", self.target_lang)
        if self.record_confidence:
            prompt_req = prompt_req.replace("[ConfRecord]", NewBing_CONF_PROMPT)
        else:
            prompt_req = prompt_req.replace("[ConfRecord]", "")
        if '"name"' in input_json:
            prompt_req = prompt_req.replace("[NamePrompt3]", NewBing_NAME_PROMPT3)
        else:
            prompt_req = prompt_req.replace("[NamePrompt3]", "")
        LOGGER.info(
            f"->{'翻译输入' if not proofread else '校对输入'}：{gptdict}\n{input_json}\n"
        )
        while True:  # 一直循环，直到得到数据
            try:
                self.request_count += 1
                LOGGER.info("->请求次数：" + str(self.request_count))
                wrote_len = 0
                resp = ""
                bing_reject = False
                force_prompt = ""
                if self.force_NewBing_hs_mode:
                    force_prompt = NewBing_FORCE_PROMPT
                async for final, response in self.chatbot.ask_stream(
                    prompt_req,
                    conversation_style=ConversationStyle.creative,
                    webpage_context=force_prompt,
                    locale="zh-cn",
                ):
                    if not final:
                        if not wrote_len:
                            if self.streamOutputMode:
                                print(response, end="")
                        else:
                            if self.streamOutputMode:
                                print(response[wrote_len:], end="")
                        sys.stdout.flush()
                        wrote_len = len(response)
                    if wrote_len > len(response):
                        bing_reject = True
                    resp = response
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                print(ex)
                traceback.print_exc()
                if "Request is throttled." in str(ex):
                    LOGGER.info("-> [请求错误]Request is throttled.")
                    self.throttled_cookie_list.append(self.current_cookie_file)
                    self.cookiefile_list.remove(self.current_cookie_file)
                    self.init_chatbot()
                    await asyncio.sleep(self.sleep_time)
                    continue
                elif "InvalidRequest" in str(ex):
                    await self.chatbot.reset()
                    continue
                elif "CAPTCHA" in str(ex):
                    LOGGER.warning("-> [请求错误]验证码拦截，需要去网页Newbing随便问一句，点击验证码，然后重新复制cookie")
                LOGGER.info("Error:%s, Please wait 30 seconds" % ex)
                traceback.print_exc()
                await asyncio.sleep(5)
                continue

            if "New topic" in str(resp):
                LOGGER.info("-> [请求错误]Need New topic")
                await self.chatbot.reset()
                continue
            
            try:
                result_text = resp["item"]["messages"][-1]["text"]
            except:
                LOGGER.error("-> [请求错误]没有获取到有效结果，重置会话")
                await self.chatbot.reset()
                continue

            if not self.streamOutputMode:
                LOGGER.info(result_text)
            else:
                print("")

            if "I'm sorry" in result_text.split("\n")[0]:
                bing_reject = True

            if "```json" in result_text:
                lang_list, code_list = extract_code_blocks(result_text)
                if len(lang_list) > 0 and len(code_list) > 0:
                    result_text = code_list[0]
            result_text = result_text[result_text.find('{"id') :]
            
            # 修复丢冒号
            result_text = (
                result_text.replace(", src:", ', "src":')
                .replace(", dst:", ', "dst":')
                .replace(", doub:", ', "doub":')
                .replace(", conf:", ', "conf":')
                .replace(", unkn:", ', "unkn":')
            )
            if not result_text.endswith("`") and not result_text.endswith("}"):
                result_text = result_text + "}"
            i = -1
            result_trans_list = []
            key_name = "dst" if not proofread else "newdst"
            error_flag = False
            for line in result_text.split("\n"):
                try:
                    line_json = json.loads(line)  # 尝试解析json
                    i += 1
                except:
                    if bing_reject and self.force_NewBing_hs_mode and i == -1:
                        LOGGER.warning(
                            "->NewBing大小姐拒绝了本次请求🙏 (forceNewBingHs enabled)\n"
                        )
                        break
                    else:
                        continue
                error_flag = False
                # 本行输出不正常
                if (
                    "id" not in line_json
                    or type(line_json["id"]) != int
                    or i > len(trans_list) - 1
                ):
                    LOGGER.error(f"->输出不正常")
                    error_flag = True
                    break
                line_id = line_json["id"]
                if line_id != trans_list[i].index:
                    LOGGER.error(f"->id不对应")
                    error_flag = True
                    break
                if key_name not in line_json or type(line_json[key_name]) != str:
                    LOGGER.error(f"->第{line_id}句不正常")
                    error_flag = True
                    break
                # 本行输出不应为空
                if trans_list[i].post_jp != "" and line_json[key_name] == "":
                    LOGGER.error(f"->第{line_id}句空白")
                    error_flag = True
                    break
                if "/" in line_json[key_name]:
                    if (
                        "／" not in trans_list[i].post_jp
                        and "/" not in trans_list[i].post_jp
                    ):
                        LOGGER.error(f"->第{line_id}句多余 / 符号：" + line_json[key_name])
                        error_flag = True
                        break

                if "Chinese" in self.target_lang:  # 统一简繁体
                    line_json[key_name] = self.opencc.convert(line_json[key_name])

                if not proofread:
                    trans_list[i].pre_zh = line_json[key_name]
                    trans_list[i].post_zh = line_json[key_name]
                    trans_list[i].trans_by = "NewBing"
                    if "conf" in line_json:
                        trans_list[i].trans_conf = line_json["conf"]
                    if "doub" in line_json:
                        trans_list[i].doub_content = line_json["doub"]
                    if "unkn" in line_json:
                        trans_list[i].unknown_proper_noun = line_json["unkn"]
                    result_trans_list.append(trans_list[i])
                else:
                    trans_list[i].proofread_zh = line_json[key_name]
                    trans_list[i].proofread_by = "NewBing"
                    trans_list[i].post_zh = line_json[key_name]
                    result_trans_list.append(trans_list[i])

            if error_flag:
                if self.skipRetry:
                    self.reset_conversation()
                    LOGGER.warning("-> 解析出错但跳过本轮翻译")
                    i = 0 if i < 0 else i
                    while i < len(trans_list):
                        if not proofread:
                            trans_list[i].pre_zh = "Failed translation"
                            trans_list[i].post_zh = "Failed translation"
                            trans_list[i].trans_by = "NewBing(Failed)"
                        else:
                            trans_list[i].proofread_zh = trans_list[i].pre_zh
                            trans_list[i].post_zh = trans_list[i].pre_zh
                            trans_list[i].proofread_by = "NewBing(Failed)"
                        result_trans_list.append(trans_list[i])
                        i = i + 1
                    return i, result_trans_list
                else:
                    await asyncio.sleep(2)
                    await self.chatbot.reset()
                    continue
            if i + 1 != len(trans_list):
                if bing_reject:
                    LOGGER.warning("->NewBing大小姐拒绝了本次请求🙏\n")
                    self.init_chatbot()
                # force_NewBing_hs_mode下newbig第一句就拒绝了，为第一句标记为失败
                if self.force_NewBing_hs_mode and bing_reject and i == -1:
                    if not proofread:
                        trans_list[0].pre_zh = "Failed translation"
                        trans_list[0].post_zh = "Failed translation"
                        trans_list[0].trans_by = "NewBing(Failed)"
                    else:
                        trans_list[0].proofread_zh = trans_list[0].pre_zh
                        trans_list[0].post_zh = trans_list[0].pre_zh
                        trans_list[0].proofread_by = "NewBing(Failed)"
                    return 1, [trans_list[0]]
                # 非force_NewBing_hs_mode下newbig拒绝了，为后面的句子标记为失败
                elif not self.force_NewBing_hs_mode and bing_reject:
                    while i + 1 < len(trans_list):
                        i = i + 1
                        if not proofread:
                            trans_list[i].pre_zh = "Failed translation"
                            trans_list[i].post_zh = "Failed translation"
                            trans_list[i].trans_by = "NewBing(Failed)"
                        else:
                            trans_list[i].proofread_zh = trans_list[i].pre_zh
                            trans_list[i].post_zh = trans_list[i].pre_zh
                            trans_list[i].proofread_by = "NewBing(Failed)"
                        result_trans_list.append(trans_list[i])

            return i + 1, result_trans_list

    async def batch_translate(
        self,
        filename,
        cache_file_path,
        trans_list: CTransList,
        num_pre_request: int,
        retry_failed: bool = False,
        gpt_dic: CGptDict = None,
        proofread: bool = False,
        retran_key: str = "",
    ) -> CTransList:
        """批量翻译

        Args:
            filename (str): 文件名
            cache_file_path (_type_): 缓存文件路径
            trans_list (CTransList): translate列表
            num_pre_request (int): 每次请求的数量
            gpt_dic (ChatgptDict, optional): _description_. Defaults to None.
            proofread (bool, optional): _description_. Defaults to False.

        Returns:
            CTransList: _description_
        """
        _, trans_list_unhit = get_transCache_from_json_new(
            trans_list,
            cache_file_path,
            retry_failed=retry_failed,
            proofread=proofread,
            retran_key=retran_key,
        )
        if self.skipH:
            LOGGER.warning("skipH: 将跳过含有敏感词的句子")
            trans_list_unhit = [
                tran
                for tran in trans_list_unhit
                if not any(word in tran.post_jp for word in H_WORDS_LIST)
            ]
            
        if len(trans_list_unhit) == 0:
            return []
        # 新文件重置chatbot
        if self.last_file_name != "" and self.last_file_name != filename:
            self.init_chatbot()
            self.last_file_name = filename

        i = 0
        trans_result_list = []
        len_trans_list = len(trans_list_unhit)
        transl_step_count = 0
        while i < len_trans_list:
            await asyncio.sleep(1)
            trans_list_split = trans_list_unhit[i : i + num_pre_request]

            # 生成dic prompt
            if gpt_dic:
                dic_prompt = gpt_dic.gen_prompt(trans_list_split)
            else:
                dic_prompt = ""

            num, trans_result = await self.translate(
                trans_list_split, dic_prompt, proofread=proofread
            )

            i += num if num > 0 else 0
            trans_result_list += trans_result
            transl_step_count+=1
            if transl_step_count>=self.save_steps:
                save_transCache_to_json(trans_list, cache_file_path)
                transl_step_count=0
            LOGGER.info("".join([repr(tran) for tran in trans_result]))
            LOGGER.info(
                f"{filename}：{str(len(trans_result_list))}/{str(len_trans_list)}"
            )

        return trans_result_list

    def reset_conversation(self):
        # await asyncio.sleep(2)
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


