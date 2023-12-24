import json, time, asyncio, os, traceback
from opencc import OpenCC
from typing import Optional
from GalTransl.ConfigHelper import CProxyPool
from GalTransl import LOGGER, LANG_SUPPORTED
from sys import exit
from GalTransl.ConfigHelper import (
    CProjectConfig,
)
from random import choice
from GalTransl.CSentense import CSentense, CTransList
from GalTransl.Cache import get_transCache_from_json, save_transCache_to_json
from GalTransl.Dictionary import CGptDict
from GalTransl.Backend.Prompts import Sakura_TRANS_PROMPT, Sakura_SYSTEM_PROMPT


class CSakuraTranslate:
    # init
    def __init__(
        self,
        config: CProjectConfig,
        type: str,
        proxy_pool: Optional[CProxyPool],
    ):
        self.type = type
        self.last_file_name = ""
        self.restore_context_mode = config.getKey("gpt.restoreContextMode")
        self.retry_count = 0

        # 跳过重试
        if val := config.getKey("skipRetry"):
            self.skipRetry = val
        else:
            self.skipRetry = False
        # 流式输出模式
        self.streamOutputMode = False
        if val := config.getKey("workersPerProject"):  # 多线程关闭流式输出
            if val > 1:
                self.streamOutputMode = False
        # 代理
        if config.getKey("internals.enableProxy") == True:
            self.proxyProvider = proxy_pool
        else:
            self.proxyProvider = None
            LOGGER.warning("不使用代理")

        # 现在只有简体
        self.opencc = OpenCC("t2s.json")

        self.init_chatbot(type=type, config=config)  # 模型初始化

        pass

    def init_chatbot(self, type, config: CProjectConfig):
        if type == "Sakura0.9":
            from GalTransl.Backend.revChatGPT.V3 import Chatbot as ChatbotV3

            endpoint = config.getBackendConfigSection("Sakura").get("endpoint")

            self.chatbot = ChatbotV3(
                api_key="sk-114514",
                proxy=self.proxyProvider.getProxy().addr
                if self.proxyProvider
                else None,
                temperature=0.1,
                top_p=0.3,
                frequency_penalty=0.0,
                system_prompt=Sakura_SYSTEM_PROMPT,
                engine="gpt-3.5-turbo",
                api_address=endpoint + "/v1/chat/completions",
            )

            self.chatbot.trans_prompt = Sakura_TRANS_PROMPT
            self.transl_style = "auto"
            self._current_style = "precies"
            self.chatbot.update_proxy(
                self.proxyProvider.getProxy().addr if self.proxyProvider else None
            )

    async def translate(self, trans_list: CTransList, gptdict=""):
        input_list = []
        for i, trans in enumerate(trans_list):
            # 处理\r\n
            if "\n" in trans.post_jp:
                trans.post_jp = trans.post_jp.replace("\n", "\\n")
            if "\r" in trans.post_jp:
                trans.post_jp = trans.post_jp.replace("\r", "\\r")

            if trans.speaker == "":
                input_list.append(trans.post_jp)
            else:
                input_list.append(f"{trans.speaker}「{trans.post_jp}」")

        input_str = "\n".join(input_list)

        prompt_req = self.chatbot.trans_prompt

        prompt_req = prompt_req.replace("[Input]", input_str)
        prompt_req = prompt_req.replace("[Glossary]", gptdict)

        while True:  # 一直循环，直到得到数据
            try:
                LOGGER.info("->输入：\n" + prompt_req + "\n")
                resp = ""
                self._del_previous_message()
                async for data in self.chatbot.ask_stream_async(prompt_req):
                    if self.streamOutputMode:
                        print(data, end="", flush=True)
                    resp += data
                print(data, end="\n")
                if not self.streamOutputMode:
                    LOGGER.info("->输出：\n" + resp)
                else:
                    print("")
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                str_ex = str(ex).lower()
                LOGGER.error(f"-> {str_ex}")
                self._del_last_answer()
                LOGGER.info("-> 报错:%s, 5秒后重试" % ex)
                await asyncio.sleep(5)
                continue

            result_text = resp.strip("\n")
            result_list = result_text.split("\n")
            # fix trick
            if result_list[0] == "——":
                result_list.pop(0)

            i = -1
            result_trans_list = []
            error_flag = False
            error_message = ""

            if len(result_list) != len(trans_list):
                error_message = f"-> 翻译结果与原文长度不一致"
                error_flag = True

            for line in result_list:
                if error_flag:
                    break
                i += 1
                # 本行输出不应为空
                if trans_list[i].post_jp != "" and line == "":
                    error_message = f"-> 第{i}句空白"
                    error_flag = True
                    break

                # 提取对话内容
                if trans_list[i].speaker != "":
                    if "「" in line:
                        line = line[line.find("「") + 1 :]
                    if line.endswith("」"):
                        line = line[:-1]
                # 统一简繁体
                line = self.opencc.convert(line)
                # 处理\r\n
                if "\n" in trans_list[i].post_jp:
                    line = line.replace("\\n", "\n")
                if "\r" in trans_list[i].post_jp:
                    line = line.replace("\\r", "\r")

                trans_list[i].pre_zh = line
                trans_list[i].post_zh = line
                trans_list[i].trans_by = "Sakura v0.9"
                result_trans_list.append(trans_list[i])

            if error_flag:
                if self.skipRetry:
                    self.reset_conversation()
                    LOGGER.warning("-> 解析出错但跳过本轮翻译")
                    while i + 1 < len(trans_list):
                        i = i + 1
                        trans_list[i].pre_zh = "Failed translation"
                        trans_list[i].post_zh = "Failed translation"
                        trans_list[i].trans_by = "Sakura v0.9(Failed)"
                        result_trans_list.append(trans_list[i])
                else:
                    self._handle_error(error_message)
                    continue
            else:
                self.retry_count = 0

            return i + 1, result_trans_list

    async def batch_translate(
        self,
        filename,
        cache_file_path,
        trans_list: CTransList,
        num_pre_request: int,
        retry_failed: bool = False,
        chatgpt_dict: CGptDict = None,
        proofread: bool = False,
        retran_key: str = "",
    ) -> CTransList:
        _, trans_list_unhit = get_transCache_from_json(
            trans_list,
            cache_file_path,
            retry_failed=retry_failed,
            proofread=False,
            retran_key=retran_key,
        )

        if len(trans_list_unhit) == 0:
            return []
        # 新文件重置chatbot
        if self.last_file_name != filename:
            self.reset_conversation()
            self.last_file_name = filename
            LOGGER.info(f"-> 开始翻译文件：{filename}")
        i = 0
        if self.restore_context_mode and len(self.chatbot.conversation["default"]) == 1:
            self.restore_context(trans_list_unhit, num_pre_request)

        trans_result_list = []
        len_trans_list = len(trans_list_unhit)
        while i < len_trans_list:
            await asyncio.sleep(5)
            trans_list_split = (
                trans_list_unhit[i : i + num_pre_request]
                if (i + num_pre_request < len_trans_list)
                else trans_list_unhit[i:]
            )

            dic_prompt = (
                chatgpt_dict.gen_prompt(trans_list_split)
                if chatgpt_dict != None
                else ""
            )

            num, trans_result = await self.translate(trans_list_split, dic_prompt)

            if num > 0:
                i += num
            result_output = ""
            for trans in trans_result:
                result_output = result_output + repr(trans)
            LOGGER.info(result_output)
            trans_result_list += trans_result
            save_transCache_to_json(trans_list, cache_file_path)
            LOGGER.info(
                f"{filename}: {str(len(trans_result_list))}/{str(len_trans_list)}"
            )

        return trans_result_list

    def _handle_error(self, error_msg: str = "") -> None:
        LOGGER.error(f"-> 错误的输出：{error_msg}")
        self.retry_count += 1
        # 切换模式
        if self.transl_style == "auto":
            self._set_gpt_style("normal")
        # 3次重试则重置会话
        if self.retry_count % 3 == 0:
            self.reset_conversation()
            LOGGER.warning("-> 3次出错重置会话")
            return
        # 10次重试则中止
        if self.retry_count > 10:
            LOGGER.error(f"-> 循环重试超过10次，已中止：{error_msg}")
            exit(-1)
        # 其他情况
        if self.type != "unoffapi":
            self._del_last_answer()
        elif self.type == "unoffapi":
            self.reset_conversation()

    def reset_conversation(self):
        self.chatbot.reset()

    def _del_previous_message(self) -> None:
        """删除历史消息，只保留最后一次的翻译结果，节约tokens"""
        last_assistant_message = None
        for message in self.chatbot.conversation["default"]:
            if message["role"] == "assistant":
                last_assistant_message = message
        system_message = self.chatbot.conversation["default"][0]
        if last_assistant_message != None:
            self.chatbot.conversation["default"] = [
                system_message,
                last_assistant_message,
            ]

    def _del_last_answer(self):
        # 删除上次输出
        if self.chatbot.conversation["default"][-1]["role"] == "assistant":
            self.chatbot.conversation["default"].pop()
        elif self.chatbot.conversation["default"][-1]["role"] is None:
            self.chatbot.conversation["default"].pop()
        # 删除上次输入
        if self.chatbot.conversation["default"][-1]["role"] == "user":
            self.chatbot.conversation["default"].pop()

    def _set_gpt_style(self, style_name: str):
        if self._current_style == style_name:
            return
        self._current_style = style_name
        if self.transl_style == "auto":
            LOGGER.info(f"-> 自动切换至{style_name}参数预设")
        else:
            LOGGER.info(f"-> 使用{style_name}参数预设")

        if style_name == "precise":
            temperature, top_p = 0.1, 0.3
            frequency_penalty, presence_penalty = 0.0, 0.0
        elif style_name == "normal":
            temperature, top_p = 0.5, 1.0
            frequency_penalty, presence_penalty = 0.2, 0.0

        self.chatbot.temperature = temperature
        self.chatbot.top_p = top_p
        self.chatbot.frequency_penalty = frequency_penalty
        self.chatbot.presence_penalty = presence_penalty

    def restore_context(self, trans_list_unhit: CTransList, num_pre_request: int):
        if trans_list_unhit[0].prev_tran == None:
            return
        tmp_context = []
        num_count = 0
        current_tran = trans_list_unhit[0].prev_tran
        while current_tran != None:
            if current_tran.pre_zh == "":
                current_tran = current_tran.prev_tran
                continue
            if current_tran.speaker!="":
                tmp_text=f"{current_tran.speaker}「{current_tran.pre_zh}」"
            else:
                tmp_text=f"{current_tran.pre_zh}"
            tmp_context.append(tmp_text)
            num_count += 1
            if num_count >= num_pre_request:
                break
            current_tran = current_tran.prev_tran

        tmp_context.reverse()
        json_lines = "\n".join(tmp_context)
        self.chatbot.conversation["default"].append(
            {
                "role": "assistant",
                "content": f"{json_lines}",
            }
        )
        LOGGER.info("-> 恢复了上下文")




if __name__ == "__main__":
    pass
