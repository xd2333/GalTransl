import sys, asyncio, traceback
from opencc import OpenCC
from typing import Optional
from random import choice
from tqdm.asyncio import tqdm as atqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from GalTransl import LOGGER, LANG_SUPPORTED
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.CSentense import CSentense, CTransList
from GalTransl.Cache import get_transCache_from_json_new, save_transCache_to_json
from GalTransl.Dictionary import CGptDict
from GalTransl.Utils import find_most_repeated_substring
from GalTransl.Backend.BaseTranslate import BaseTranslate
from GalTransl.Backend.Prompts import (
    Sakura_TRANS_PROMPT,
    Sakura_SYSTEM_PROMPT,
    Sakura_TRANS_PROMPT010,
    Sakura_SYSTEM_PROMPT010,
    GalTransl_SYSTEM_PROMPT,
    GalTransl_TRANS_PROMPT,
)
from GalTransl import transl_counter


class CSakuraTranslate(BaseTranslate):
    # init
    def __init__(
        self,
        config: CProjectConfig,
        eng_type: str,
        endpoint: str,
        proxy_pool: Optional[CProxyPool],
    ):
        self.projectConfig = config
        self.eng_type = eng_type
        self.endpoint = endpoint
        self.last_file_name = ""
        self.restore_context_mode = config.getKey("gpt.restoreContextMode")
        self.retry_count = 0

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
        # 保存间隔
        if val := config.getKey("save_steps"):
            self.save_steps = val
        else:
            self.save_steps = 1
        # 跳过重试
        if val := config.getKey("skipRetry"):
            self.skipRetry = val
        else:
            self.skipRetry = False
        # 流式输出模式
        if val := config.getKey("gpt.streamOutputMode"):
            self.streamOutputMode = val
        else:
            self.streamOutputMode = False
        # 多线程关闭流式输出
        if val := config.getKey("workersPerProject"):
            if val > 1:
                self.streamOutputMode = False
        # 代理
        if config.getKey("internals.enableProxy") == True:
            self.proxyProvider = proxy_pool
        else:
            self.proxyProvider = None
        # transl_style（废弃）
        if val := config.getKey("gpt.transl_style"):
            self.transl_style = val
        else:
            self.transl_style = "流畅"
        # transl_dropout
        if val := config.getKey("gpt.transl_dropout"):
            self.transl_dropout = val
        else:
            self.transl_dropout = 0
        # token_limit
        if val := config.getKey("gpt.token_limit"):
            self.token_limit = val
            import tiktoken

            self.tokenizer = tiktoken.get_encoding("o200k_base")
        else:
            self.token_limit = 0
            self.tokenizer = None

        if self.target_lang == "Simplified_Chinese":
            self.opencc = OpenCC("t2s.json")
        elif self.target_lang == "Traditional_Chinese":
            self.opencc = OpenCC("s2tw.json")

        self.init_chatbot(eng_type=eng_type, config=config)  # 模型初始化

        pass

    def init_chatbot(self, eng_type, config: CProjectConfig):
        from GalTransl.Backend.revChatGPT.V3 import Chatbot as ChatbotV3

        backendSpecific = config.projectConfig["backendSpecific"]
        section_name = "SakuraLLM" if "SakuraLLM" in backendSpecific else "Sakura"
        endpoint = self.endpoint
        endpoint = endpoint[:-1] if endpoint.endswith("/") else endpoint
        eng_name = config.getBackendConfigSection(section_name).get(
            "rewriteModelName", "gpt-3.5-turbo"
        )
        if eng_type == "sakura-009":
            self.system_prompt = Sakura_SYSTEM_PROMPT
            self.trans_prompt = Sakura_TRANS_PROMPT
        if eng_type == "sakura-v1.0":
            self.system_prompt = Sakura_SYSTEM_PROMPT010
            self.trans_prompt = Sakura_TRANS_PROMPT010
        if "galtransl" in eng_type:
            self.system_prompt = GalTransl_SYSTEM_PROMPT
            self.trans_prompt = GalTransl_TRANS_PROMPT
        self.chatbot = ChatbotV3(
            api_key="sk-114514",
            system_prompt=self.system_prompt,
            engine=eng_name,
            api_address=endpoint + "/v1/chat/completions",
            timeout=60,
        )
        self.chatbot.update_proxy(
            self.proxyProvider.getProxy().addr if self.proxyProvider else None  # type: ignore
        )
        self._current_temp_type = "precies"
        self._set_temp_type("precise")

    def clean_up(self):
        endpointQueue = self.projectConfig.endpointQueue
        endpointQueue.put_nowait(self.endpoint)

    async def translate(self, trans_list: CTransList, gptdict=""):
        input_list = []
        max_repeat = 0
        line_lens = []
        for i, trans in enumerate(trans_list):
            # 处理换行
            if self.eng_type in ["sakura-009"]:
                tmp_text = trans.post_jp.replace("\r\n", "↓↓").replace("\n", "↓↓")
            else:
                tmp_text = trans.post_jp.replace("\r\n", "\\n").replace("\n", "\\n")
            # 有name
            if trans.speaker != "":
                tmp_text = f"{trans.speaker}「{tmp_text}」"
            input_list.append(tmp_text)
            _, count = find_most_repeated_substring(tmp_text)
            max_repeat = max(max_repeat, count)
            line_lens.append(len(tmp_text))
        input_str = "\n".join(input_list).strip("\n")

        if self.token_limit > 0 and self.tokenizer:
            check_pass_flag = False
            while not check_pass_flag:
                input_str = "\n".join(input_list).strip("\n")
                history = self._get_gpt_history()
                prompt_req = (
                    self.trans_prompt.replace("[Input]", input_str)
                    .replace("[Glossary]", gptdict)
                    .replace("[tran_style]", self.transl_style)
                )

                all_tokens = len(self.tokenizer.encode(history + prompt_req))
                if all_tokens <= self.token_limit:
                    check_pass_flag = True
                else:
                    if len(input_list) > 1:
                        input_list = input_list[:-1]
                        trans_list = trans_list[:-1]
                        line_lens = line_lens[:-1]
                        continue
                    elif len(self.chatbot.conversation["default"]) > 1:
                        self.reset_conversation()
                        continue
                    else:
                        LOGGER.error(
                            f"-> 输入超出token限制，且无法再减少，请检查输入的文本"
                        )
                        check_pass_flag = True

        # 检测退化阈值
        self.JP_REPETITION_THRESHOLD_LINE = max_repeat
        _, self.JP_REPETITION_THRESHOLD_ALL = find_most_repeated_substring(input_str)
        self.JP_LINE_LENS = line_lens

        prompt_req = self.trans_prompt
        prompt_req = prompt_req.replace("[Input]", input_str)
        prompt_req = prompt_req.replace("[Glossary]", gptdict)
        prompt_req = prompt_req.replace("[tran_style]", self.transl_style)

        once_flag = False

        while True:  # 一直循环，直到得到数据
            try:
                with logging_redirect_tqdm(loggers=[LOGGER]):
                    LOGGER.info("->输入：\n" + gptdict + "\n" + repr(input_str))
                print("\n", flush=True)
                resp = ""
                last_data = ""
                repetition_cnt = 0
                degen_flag = False
                self._del_previous_message()
                ask_stream = self.chatbot.ask_stream_async(prompt_req)
                token_count = 0
                async for data in ask_stream:
                    token_count += 1
                    if self.streamOutputMode:
                        print(data, end="", flush=True)
                    resp += data
                    # 检测是否反复重复输出同一内容，如果超过一定次数，则判定为退化并打断。
                    if token_count % 4 == 0:  # 每4个token检测一次
                        degen_flag = self.check_degen_in_process(resp)
                        if degen_flag:
                            await ask_stream.aclose()
                            break
                if not degen_flag:  # 结束时再检测一次
                    degen_flag = self.check_degen_in_process(resp)
                # print(data, end="\n")
                if not self.streamOutputMode:
                    LOGGER.info("->输出：\n" + repr(resp))
                else:
                    print("")
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                str_ex = str(ex).lower()
                traceback.print_exc()
                self._del_last_answer()
                LOGGER.info("-> [请求错误]报错:%s, 即将重试" % ex)
                await asyncio.sleep(3)
                continue

            resp = resp.replace("*EOF*", "").strip()
            result_list = resp.strip("\n").split("\n")
            # fix trick
            if result_list[0] == "——":
                result_list.pop(0)

            i = -1
            result_trans_list = []
            error_flag = False
            error_message = ""

            if degen_flag:
                error_message = f"-> 生成过程中检测到大概率为退化的特征"
                error_flag = True

            elif len(result_list) != len(trans_list):
                error_message = f"-> 翻译结果与原文长度不一致"
                error_flag = True

            for line in result_list:
                if error_flag:
                    break
                i += 1
                # 本行输出不应为空
                if trans_list[i].post_jp != "" and line == "":
                    error_message = f"-> 第{i+1}句空白"
                    error_flag = True
                    break

                # 提取对话内容
                if trans_list[i].speaker != "":
                    if "「" in line:
                        line = line[line.find("「") + 1 :]
                    if line.endswith("」"):
                        line = line[:-1]
                    if line.endswith("」。") or line.endswith("」."):
                        line = line[:-2]
                # 统一简繁体
                line = self.opencc.convert(line)
                # 还原换行
                if "\r\n" in trans_list[i].post_jp:
                    line = line.replace("↓↓", "\r\n").replace("\\n", "\r\n")
                elif "\n" in trans_list[i].post_jp:
                    line = line.replace("↓↓", "\n").replace("\\n", "\n")

                # fix trick
                if line.startswith("："):
                    line = line[1:]

                trans_list[i].pre_zh = line
                trans_list[i].post_zh = line
                trans_list[i].trans_by = self.eng_type
                result_trans_list.append(trans_list[i])

            if error_flag:
                transl_counter["error_count"]+=1
                LOGGER.debug(f"错误计数：{transl_counter['error_count']}")
                LOGGER.debug(f"翻译句数：{transl_counter['tran_count']}")
                LOGGER.debug(f"千句错误率：{transl_counter['error_count']/min(transl_counter['tran_count'],1)*1000:.2f}")

                if self.skipRetry:
                    self.reset_conversation()
                    LOGGER.warning("-> 解析出错但跳过本轮翻译")
                    i = 0 if i < 0 else i
                    while i < len(trans_list):
                        trans_list[i].pre_zh = "Failed translation"
                        trans_list[i].post_zh = "Failed translation"
                        trans_list[i].trans_by = f"{self.eng_type}(Failed)"
                        result_trans_list.append(trans_list[i])
                        i = i + 1
                else:
                    LOGGER.error(f"-> 错误的输出：{error_message}")
                    # 删除上次回答与提问
                    self._del_last_answer()
                    await asyncio.sleep(1)
                    if degen_flag:
                        self._set_temp_type("normal")
                        # 先增加frequency_penalty参数重试再进行二分
                        if not once_flag:
                            once_flag = True
                            continue
                    # 可拆分先对半拆
                    if len(trans_list) > 1:
                        LOGGER.warning("-> 对半拆分重试")
                        half_len = len(trans_list) // 3
                        half_len = 1 if half_len < 1 else half_len
                        return await self.translate(trans_list[:half_len], gptdict)
                    # 拆成单句后，才开始计算重试次数
                    self.retry_count += 1
                    # 5次重试则填充原文
                    if self.retry_count >= 5:
                        LOGGER.error(
                            f"-> 单句循环重试{self.retry_count}次出错，填充原文"
                        )
                        i = 0 if i < 0 else i
                        while i < len(trans_list):
                            trans_list[i].pre_zh = trans_list[i].post_jp
                            trans_list[i].post_zh = trans_list[i].post_jp
                            trans_list[i].trans_by = f"{self.eng_type}(Failed)"
                            result_trans_list.append(trans_list[i])
                            i = i + 1
                        return i, result_trans_list
                    # 2次重试则重置会话
                    elif self.retry_count % 2 == 0:
                        self.reset_conversation()
                        LOGGER.warning(
                            f"-> 单句循环重试{self.retry_count}次出错，重置会话"
                        )
                        continue
                    continue
            else:
                self.retry_count = 0

            self._set_temp_type("precise")
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
        _, trans_list_unhit = get_transCache_from_json_new(
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
        transl_step_count = 0
        progress_bar = atqdm(
            total=len_trans_list,
            desc=f"Translating {filename}",
            unit="line",
            dynamic_ncols=True,
            leave=False,
            file=sys.stdout,
        )
        while i < len_trans_list:
            # await asyncio.sleep(1)

            trans_list_split = trans_list_unhit[i : i + num_pre_request]
            dic_prompt = (
                gpt_dic.gen_prompt(trans_list_split, type="sakura")
                if gpt_dic != None
                else ""
            )

            num, trans_result = await self.translate(trans_list_split, dic_prompt)

            if self.transl_dropout > 0 and num == num_pre_request:
                if self.transl_dropout < num:
                    num -= self.transl_dropout
                    trans_result = trans_result[:num]

            i += num if num > 0 else 0
            transl_counter["tran_count"]+=num
            transl_step_count += 1
            if transl_step_count >= self.save_steps:
                save_transCache_to_json(trans_list, cache_file_path)
                transl_step_count = 0

            trans_result_list += trans_result
            progress_bar.update(num)
            print("\n", flush=True)
            LOGGER.info("".join([repr(tran) for tran in trans_result]))
        progress_bar.close()

        return trans_result_list

    def reset_conversation(self):
        self.chatbot.reset()

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
                last_user_message["content"] = ""
        system_message = self.chatbot.conversation["default"][0]
        self.chatbot.conversation["default"] = [system_message]
        if last_user_message:
            self.chatbot.conversation["default"].append(last_user_message)
        if last_assistant_message:
            last_assistant_message["content"] = (
                last_assistant_message["content"].replace("*EOF*", "").strip()
            )
            if self.transl_dropout > 0:
                sp = last_assistant_message["content"].split("\n")
                if len(sp) > self.transl_dropout:
                    sp = sp[: 0 - self.transl_dropout]
                    last_assistant_message["content"] = "\n".join(sp)
            self.chatbot.conversation["default"].append(last_assistant_message)

    def _del_last_answer(self):
        # 删除上次输出
        if self.chatbot.conversation["default"][-1]["role"] == "assistant":
            self.chatbot.conversation["default"].pop()
        elif self.chatbot.conversation["default"][-1]["role"] is None:
            self.chatbot.conversation["default"].pop()
        # 删除上次输入
        if self.chatbot.conversation["default"][-1]["role"] == "user":
            self.chatbot.conversation["default"].pop()

    def _set_temp_type(self, style_name: str):
        if self._current_temp_type == style_name:
            return
        self._current_temp_type = style_name

        if style_name == "precise":
            temperature, top_p = 0.1, 0.8
            frequency_penalty, presence_penalty = 0.1, 0.0
        elif style_name == "normal":
            temperature, top_p = 0.4, 0.95
            frequency_penalty, presence_penalty = 0.3, 0.0

        if "galtransl" in self.eng_type:
            if style_name == "precise":
                temperature, top_p = 0.2, 0.8
                frequency_penalty, presence_penalty = 0.1, 0.0
            elif style_name == "normal":
                temperature, top_p = 0.6, 0.95
                frequency_penalty, presence_penalty = 0.3, 0.0

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
            if current_tran.speaker != "":
                tmp_text = f"{current_tran.speaker}「{current_tran.pre_zh}」"
            else:
                tmp_text = f"{current_tran.pre_zh}"
            tmp_context.append(tmp_text)
            num_count += 1
            if num_count >= num_pre_request:
                break
            current_tran = current_tran.prev_tran

        tmp_context.reverse()
        json_lines = "\n".join(tmp_context)
        self.chatbot.conversation["default"].append(
            {
                "role": "user",
                "content": f"(历史翻译请求)",
            }
        )
        self.chatbot.conversation["default"].append(
            {
                "role": "assistant",
                "content": f"{json_lines}",
            }
        )
        LOGGER.info("-> 恢复了上下文")

    def check_degen_in_process(self, cn: str = ""):

        line_count = cn.count("\n") + 1
        if line_count < len(self.JP_LINE_LENS):  # 长度不超当前行直接放行
            if len(cn.split("\n")[-1]) < self.JP_LINE_LENS[line_count - 1]:
                return False
        else:  # 行数超过当前行，某行反复输出的情况
            repeated_str, repeated_count = find_most_repeated_substring(cn)
            if repeated_count > max(self.JP_REPETITION_THRESHOLD_ALL * 2, 12):
                return True

        # 行内反复输出的情况
        last_line = cn.split("\n")[-1]
        repeated_str, repeated_count = find_most_repeated_substring(last_line)
        if repeated_count > max(self.JP_REPETITION_THRESHOLD_LINE * 2, 12):
            return True

        return False

    def _get_gpt_history(self):
        gpt_history = []
        for message in self.chatbot.conversation["default"]:
            gpt_history.append(message["content"])
        return "\n".join(gpt_history)


if __name__ == "__main__":
    pass
