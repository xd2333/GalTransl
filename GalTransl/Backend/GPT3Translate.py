import os
import json
import time
import asyncio
import traceback

from opencc import OpenCC
from typing import List, Optional
from random import choice
from GalTransl.CSentense import *
from GalTransl.ConfigHelper import (
    CProjectConfig,
)
from GalTransl.COpenAI import COpenAIToken, COpenAITokenPool, initGPTToken
from GalTransl.ConfigHelper import CProxyPool
from GalTransl.Dictionary import CGptDict
from GalTransl.Cache import get_transCache_from_json_new, save_transCache_to_json
from GalTransl.Backend.revChatGPT.typings import APIConnectionError
from GalTransl.Utils import extract_code_blocks, fix_quotes
from httpx import ProtocolError
from GalTransl import LOGGER, LANG_SUPPORTED
from GalTransl.Backend.BaseTranslate import BaseTranslate
from GalTransl.Backend.Prompts import (
    GPT35_0613_NAME_PROMPT3,
    GPT35_0613_TRANS_PROMPT,
    GPT35_0613_SYSTEM_PROMPT,
    GPT35_1106_SYSTEM_PROMPT,
    GPT35_1106_NAME_PROMPT3,
    GPT35_1106_TRANS_PROMPT,
    H_WORDS_LIST,
)


class CGPT35Translate(BaseTranslate):
    def __init__(
        self,
        config: CProjectConfig,
        eng_type: str,
        proxy_pool: Optional[CProxyPool],
        token_pool: COpenAITokenPool,
    ):
        self.eng_type = eng_type
        self.last_file_name = ""
        self.retry_count = 0
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
        # 429等待时间
        if val := config.getKey("gpt.tooManyRequestsWaitTime"):
            self.wait_time = val
        else:
            self.wait_time = 60
        # 换行符改善模式
        if val := config.getKey("gpt.lineBreaksImprovementMode"):
            self.line_breaks_improvement_mode = val
        else:
            self.line_breaks_improvement_mode = False
        # 恢复上下文模式
        if val := config.getKey("gpt.restoreContextMode"):
            self.restore_context_mode = val
        else:
            self.restore_context_mode = False
        # 跳过h
        if val := config.getKey("skipH"):
            self.skipH = val
        else:
            self.skipH = False
        # enhance_jailbreak
        if val := config.getKey("gpt.enhance_jailbreak"):
            self.enhance_jailbreak = val
        else:
            self.enhance_jailbreak = False
        # 跳过重试
        if val := config.getKey("skipRetry"):
            self.skipRetry = val
        else:
            self.skipRetry = False
        # 挥霍token模式
        if val := config.getKey("gpt.fullContextMode"):
            self.full_context_mode = val
        else:
            self.full_context_mode = False
        # 流式输出模式
        if val := config.getKey("gpt.streamOutputMode"):
            self.streamOutputMode = val
        else:
            self.streamOutputMode = False
        if val := config.getKey("workersPerProject"):  # 多线程关闭流式输出
            if val > 1:
                self.streamOutputMode = False

        self.tokenProvider = token_pool
        if config.getKey("internals.enableProxy") == True:
            self.proxyProvider = proxy_pool
        else:
            self.proxyProvider = None
            
        self._current_temp_type = ""

        if self.target_lang == "Simplified_Chinese":
            self.opencc = OpenCC("t2s.json")
        elif self.target_lang == "Traditional_Chinese":
            self.opencc = OpenCC("s2tw.json")

        self.init_chatbot(eng_type=eng_type, config=config)  # 模型选择
        pass

    def init(self) -> bool:
        """
        call it before jobs
        """
        pass

    def init_chatbot(self, eng_type, config):
        eng_name = config.getBackendConfigSection("GPT35").get("rewriteModelName", "")

        if eng_type == "gpt35-0613":
            from GalTransl.Backend.revChatGPT.V3 import Chatbot as ChatbotV3

            self.token = self.tokenProvider.getToken(True, False)
            eng_name = "gpt-3.5-turbo-0613" if eng_name == "" else eng_name
            # it's a workarounds, and we'll replace this soloution with a custom OpenAI API wrapper?
            self.chatbot = ChatbotV3(
                api_key=self.token.token,
                engine=eng_name,
                system_prompt=GPT35_0613_SYSTEM_PROMPT,
                api_address=self.token.domain + "/v1/chat/completions",
                timeout=30,
            )
            self.trans_prompt = GPT35_0613_TRANS_PROMPT
            self.name_prompt = GPT35_0613_NAME_PROMPT3
            self.chatbot.update_proxy(
                self.proxyProvider.getProxy().addr if self.proxyProvider else None  # type: ignore
            )
        elif eng_type == "gpt35-1106":
            from GalTransl.Backend.revChatGPT.V3 import Chatbot as ChatbotV3

            self.token = self.tokenProvider.getToken(True, False)
            eng_name = "gpt-3.5-turbo-1106" if eng_name == "" else eng_name
            # it's a workarounds, and we'll replace this soloution with a custom OpenAI API wrapper?
            self.chatbot = ChatbotV3(
                api_key=self.token.token,
                engine=eng_name,
                system_prompt=GPT35_1106_SYSTEM_PROMPT,
                api_address=self.token.domain + "/v1/chat/completions",
                timeout=30,
                response_format="json",
            )
            self.trans_prompt = GPT35_1106_TRANS_PROMPT
            self.name_prompt = GPT35_1106_NAME_PROMPT3
            self.chatbot.update_proxy(
                self.proxyProvider.getProxy().addr if self.proxyProvider else None  # type: ignore
            )

        self._set_temp_type("precise")


    async def asyncTranslate(self, content: CTransList, gptdict="") -> CTransList:
        """
        translate with async requests
        """
        input_list = []
        for i, trans in enumerate(content):
            tmp_obj = {"id": trans.index, "name": trans.speaker, "src": trans.post_jp}
            if trans.speaker == "":
                del tmp_obj["name"]
            input_list.append(tmp_obj)
        input_json = json.dumps(input_list, ensure_ascii=False)
        prompt_req = self.trans_prompt
        prompt_req = prompt_req.replace("[Input]", input_json)
        prompt_req = prompt_req.replace("[Glossary]", gptdict)
        prompt_req = prompt_req.replace("[SourceLang]", self.source_lang)
        prompt_req = prompt_req.replace("[TargetLang]", self.target_lang)
        if '"name"' in input_json:
            prompt_req = prompt_req.replace("[NamePrompt3]", self.name_prompt)
        else:
            prompt_req = prompt_req.replace("[NamePrompt3]", "")
        if self.enhance_jailbreak:
            assistant_prompt = "```jsonline"
        else:
            assistant_prompt = ""
        while True:  # 一直循环，直到得到数据
            try:
                # change token
                if self.eng_type != "unoffapi":
                    self.token = self.tokenProvider.getToken(True, False)
                    self.chatbot.set_api_key(self.token.token)
                    self.chatbot.set_api_addr(
                        f"{self.token.domain}/v1/chat/completions"
                    )
                LOGGER.info(f"-> 翻译输入：\n{gptdict}\n{input_json}\n")
                if self.streamOutputMode:
                    LOGGER.info("-> 输出：\n")
                resp, data = "", ""
                if self.eng_type != "unoffapi":
                    if not self.full_context_mode:
                        self._del_previous_message()
                    async for data in self.chatbot.ask_stream_async(prompt_req,assistant_prompt=assistant_prompt):
                        if self.streamOutputMode:
                            print(data, end="", flush=True)
                        resp += data
                if self.eng_type == "unoffapi":
                    for data in self.chatbot.ask(prompt_req):
                        async for data in self.chatbot.ask_async(prompt_req):
                            if self.streamOutputMode:
                                print(data["message"][len(resp) :], end="", flush=True)
                                resp = data["message"]
                if not self.streamOutputMode:
                    LOGGER.info(f"-> 输出：\n{resp}")
                else:
                    print("")
            except Exception as ex:
                str_ex = str(ex).lower()
                LOGGER.error(f"-> {str_ex}")
                if "quota" in str_ex:
                    self.tokenProvider.reportTokenProblem(self.token)
                    LOGGER.error(f"-> [请求错误]余额不足： {self.token.maskToken()}")
                    self.token = self.tokenProvider.getToken(True, False)
                    self.chatbot.set_api_key(self.token.token)
                elif "try again later" in str_ex or "too many requests" in str_ex:
                    LOGGER.warning(f"-> [请求错误]请求受限，{self.wait_time}秒后继续尝试")
                    await asyncio.sleep(self.wait_time)
                    continue
                elif "try reload" in str_ex:
                    self.reset_conversation()
                    LOGGER.error("-> [请求错误]报错重置会话")
                    continue

                self._del_last_answer()
                LOGGER.error(f"-> [请求错误]报错, 5秒后重试")
                await asyncio.sleep(5)
                continue

            if "```json" in resp:
                lang_list, code_list = extract_code_blocks(resp)
                if len(lang_list) > 0 and len(code_list) > 0:
                    result_text = code_list[0]
                else:
                    result_text = resp
            elif "[{" in resp:
                result_text = resp[resp.find("[{") : resp.rfind("}]") + 2].strip()
            else:
                result_text = resp
            result_text = fix_quotes(result_text)

            key_name = "dst"
            error_flag, warn_flag = False, False
            error_message = ""
            try:
                result_json = json.loads(result_text)  # 尝试解析json
                if len(result_json) != len(input_list):  # 输出行数错误
                    LOGGER.error("-> [解析错误]错误的输出行数：\n" + result_text + "\n")
                    error_message = "输出行数错误"
                    error_flag = True
            except:
                LOGGER.error("-> [解析错误]非json：\n" + result_text + "\n")
                error_message = "输出非json"
                error_flag = True

            if not error_flag:
                # 解析后检查
                for i, result in enumerate(result_json):
                    # 本行输出不正常
                    if key_name not in result or type(result[key_name]) != str:
                        error_message = f"第{content[i].index}句找不到{key_name}"
                        error_flag = True
                        break
                    # 本行输出不应为空
                    if content[i].post_jp != "" and result[key_name] == "":
                        error_message = f"第{content[i].index}句空白"
                        error_flag = True
                        break
                    # 本行输出有多余的 /
                    if "/" in result[key_name] and not any(
                        char in content[i].post_jp for char in ["／", "/", "・"]
                    ):
                        error_message = f"第{content[i].index}句多余 / 符号"
                        error_flag = True
                        break
                    # 丢name
                    if "name" not in result and content[i].speaker != "":
                        error_message = f"第{content[i].index}句丢 name"
                        warn_flag = True
                    # 多余name
                    if "name" in result and content[i].speaker == "":
                        error_message = f"第{content[i].index}句多 name"
                        warn_flag = True

            # if self.line_breaks_improvement_mode and len(input_list) > 3:
            #     if "\\r\\n" in input_json and "\\r\\n" not in result_text:
            #         error_message = "换行符改善模式"
            #         error_flag = True

            if error_flag:
                LOGGER.error(f"-> [解析错误]解析结果出错：{error_message}")
                # 跳过重试
                if self.skipRetry:
                    self.reset_conversation()
                    LOGGER.warning("-> [解析错误]解析出错但直接跳过本轮翻译")
                    i = 0
                    while i < len(content):
                        content[i].pre_zh = "Failed translation"
                        content[i].post_zh = "Failed translation"
                        content[i].trans_by = f"{self.chatbot.engine}(Failed)"
                        i = i + 1
                    return len(content), content

                # 重试逻辑
                await asyncio.sleep(1)
                self.retry_count += 1

                if self.eng_type != "unoffapi":
                    self._del_last_answer()
                elif self.eng_type == "unoffapi":
                    self.reset_conversation()
                # 先切换模式
                self._set_temp_type("normal")
                # 2次重试则对半拆
                if self.retry_count == 2 and len(content) > 1:
                    self.retry_count -= 1
                    LOGGER.warning("-> 仍然出错，拆分重试")
                    return await self.asyncTranslate(
                        content[: len(content) // 2], gptdict
                    )
                # 单句重试仍错则重置会话
                if self.retry_count == 3:
                    self.reset_conversation()
                    LOGGER.warning("-> [解析错误]单句仍错，重置会话")
                # 单句5次重试则中止
                if self.retry_count == 5:
                    raise RuntimeError(
                        f"-> [解析错误]单句反复出错，已中止。最后错误为：{error_message}"
                    )
                continue

            if warn_flag:
                LOGGER.warning(f"-> [解析错误]解析结果有问题：{error_message}")
                await asyncio.sleep(1)

            for i, result in enumerate(result_json):  # 正常输出
                if "Chinese" in self.target_lang:  # 统一简繁体
                    result[key_name] = self.opencc.convert(result[key_name])
                content[i].pre_zh = result[key_name]
                content[i].post_zh = result[key_name]
                content[i].trans_by = self.chatbot.engine

            if not warn_flag:
                self._set_temp_type("precise")
            self.retry_count = 0

            break  # 输出正确，跳出循环
        return len(content), content

    def reset_conversation(self):
        if self.eng_type != "unoffapi":
            self.chatbot.reset()
        elif self.eng_type == "unoffapi":
            self.chatbot.reset_chat()

    def _del_previous_message(self) -> None:
        """删除历史消息，只保留最后一次的翻译结果，节约tokens"""
        last_assistant_message = None
        last_user_message = None
        for message in self.chatbot.conversation["default"]:
            if message["role"] == "assistant":
                last_assistant_message = message
        for message in self.chatbot.conversation["default"]:
            if message["role"] == "user":
                last_user_message = message
                last_user_message["content"] = "(History Translation Request)"
        system_message = self.chatbot.conversation["default"][0]
        self.chatbot.conversation["default"] = [system_message]
        if last_user_message:
            self.chatbot.conversation["default"].append(last_user_message)
        if last_assistant_message:
            self.chatbot.conversation["default"].append(last_assistant_message)

    def _del_last_answer(self):
        if self.eng_type != "unoffapi":
            # 删除上次输出
            if self.chatbot.conversation["default"][-1]["role"] == "assistant":
                self.chatbot.conversation["default"].pop()
            elif self.chatbot.conversation["default"][-1]["role"] is None:
                self.chatbot.conversation["default"].pop()
            # 删除上次输入
            if self.chatbot.conversation["default"][-1]["role"] == "user":
                self.chatbot.conversation["default"].pop()
        elif self.eng_type == "unoffapi":
            pass

    def _set_temp_type(self, style_name: str):
        if self.eng_type == "unoffapi":
            return
        if self._current_temp_type == style_name:
            return
        self._current_temp_type = style_name

        if style_name == "precise":
            temperature, top_p = 1.0, 0.4
            frequency_penalty, presence_penalty = 0.3, 0.0
        else:  # normal default
            temperature, top_p = 1.0, 1.0
            frequency_penalty, presence_penalty = 0.2, 0.0
        if self.eng_type != "unoffapi":
            self.chatbot.temperature = temperature
            self.chatbot.top_p = top_p
            self.chatbot.frequency_penalty = frequency_penalty
            self.chatbot.presence_penalty = presence_penalty

    def restore_context(self, trans_list_unhit: CTransList, num_pre_request: int):
        if self.eng_type != "unoffapi":
            if len(trans_list_unhit) == 0 or trans_list_unhit[0].prev_tran == None:
                return
            tmp_context = []
            num_count = 0
            current_tran = trans_list_unhit[0].prev_tran
            while current_tran != None:
                if current_tran.pre_zh == "":
                    current_tran = current_tran.prev_tran
                    continue
                tmp_obj = {
                    "id": current_tran.index,
                    "name": current_tran._speaker,
                    "dst": current_tran.pre_zh,
                }
                if current_tran._speaker == "":
                    del tmp_obj["name"]
                tmp_context.append(tmp_obj)
                num_count += 1
                if num_count >= num_pre_request:
                    break
                current_tran = current_tran.prev_tran

            tmp_context.reverse()
            self.chatbot.conversation["default"].append(
                {"role": "user", "content": "(History Translation Request)"}
            )
            self.chatbot.conversation["default"].append(
                {
                    "role": "assistant",
                    "content": "Transl: " + json.dumps(tmp_context, ensure_ascii=False),
                }
            )
            LOGGER.info("-> 恢复了上下文")

        elif self.eng_type == "unoffapi":
            pass

    async def batch_translate(
        self,
        filename,
        cache_path,
        trans_list: CTransList,
        num_pre_req: int,
        retry_failed: bool = False,
        gpt_dic: CGptDict = None,
        proofread: bool = False,
        retran_key: str = "",
    ) -> CTransList:
        _, trans_list_unhit = get_transCache_from_json_new(
            trans_list,
            cache_path,
            retry_failed=retry_failed,
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
        if self.last_file_name != filename:
            self.reset_conversation()
            self.last_file_name = filename
            LOGGER.info(f"-> 开始翻译文件：{filename}")

        # 恢复上下文
        if (
            self.eng_type != "unoffapi"
            and self.restore_context_mode
            and len(self.chatbot.conversation["default"]) == 1
        ):
            self.restore_context(trans_list_unhit, num_pre_req)

        i = 0
        trans_result_list = []
        len_trans_list = len(trans_list_unhit)
        transl_step_count = 0
        while i < len_trans_list:
            await asyncio.sleep(1)
            trans_list_split = trans_list_unhit[i : i + num_pre_req]

            dic_prompt = ""
            if gpt_dic != None:
                dic_prompt = gpt_dic.gen_prompt(trans_list_split)
            num, trans_result = await self.asyncTranslate(trans_list_split, dic_prompt)
            trans_result_list += trans_result
            i += num if num > 0 else 0

            transl_step_count+=1
            if transl_step_count>=self.save_steps:
                save_transCache_to_json(trans_list, cache_path)
                transl_step_count=0
            LOGGER.info("".join([repr(tran) for tran in trans_result]))
            LOGGER.info(f"{filename}: {len(trans_result_list)}/{len_trans_list}")

        return trans_result_list

    pass
