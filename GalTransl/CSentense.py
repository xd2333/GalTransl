from typing import List


class CSentense:
    """
    每个CSentense储存一句待翻译文本
    """

    def __init__(self, pre_jp: str, speaker: str = "", index=0) -> None:
        """每个CSentense储存一句待翻译文本

        Args:
            pre_jp (str): 润色前日文
            speaker (str, optional): 说话人. Defaults to "".
            index_key (str, optional): 唯一index. Defaults to "".
        """
        self.index = index

        self.pre_jp = pre_jp  # 前原
        self.post_jp = pre_jp  # 前润，初始为原句
        self.pre_zh = ""  # 后原
        self.proofread_zh = ""  # 校对, For GPT4
        self.post_zh = ""  # 后润，最终zh

        self.speaker = speaker  # 如果是dialogue则可以记录讲话者
        self._speaker = speaker  # 用于记录原speaker，因为speaker会被改变
        self.is_dialogue = True if speaker != "" else False  # 记录原句是否为对话
        self.has_diag_symbol = False  # 是对话但也可能没有对话框，所以分开
        self.left_symbol = ""  # 记录原句的左对话框与其他左边符号等
        self.right_symbol = ""  # 记录原句的右对话框与其他右边符号等

        self.dia_format = "#句子"  # 这两个主要是字典替换的时候要
        self.mono_format = "#句子"  # 用在>关键字中

        self.trans_by = ""  # 翻译记录
        self.proofread_by = ""  # 校对记录

        self.problem = ""  # 问题记录
        self.trans_conf = 0.0  # 翻译可信度 For GPT4
        self.doub_content = ""  # 用于记录疑问句的内容 For GPT4
        self.unknown_proper_noun = ""  # 用于记录未知的专有名词 For GPT4

        self.prev_tran: CSentense = None  # 指向上一个tran
        self.next_tran: CSentense = None  # 指向下一个tran

    def __repr__(self) -> str:
        tmp_post_jp = self.post_jp.replace("\r\n", "\\r\\n")
        tmp_post_zh = self.post_zh.replace("\r\n", "\\r\\n")
        tmp_proofread_zh = self.proofread_zh.replace("\r\n", "\\r\\n")
        char_t = "\t"
        char_n = "\n"
        return f"{char_n}---> {self.index}{char_n}> JP: {tmp_post_jp}{char_n}> CN: {tmp_post_zh if self.proofread_zh == '' else tmp_proofread_zh}"

    def analyse_dialogue(self, dia_format: str = "#句子", mono_format: str = "#句子"):
        """对话分析，根据对话框判断是否为对话，暂时隐藏对话框，分别格式化diag与mono到不同的format

        Args:
            dia_format (str, optional): 对于对话的格式化，会把#句子替换为原句. Defaults to "#句子".
            # 句子替换为原句. Defaults to "#句子".
            mono_format (str, optional): 对于独白的格式化，会把
        """
        if self.post_jp == "":
            return
        self.dia_format, self.mono_format = dia_format, mono_format
        first_symbol, last_symbol = self.post_jp[:1], self.post_jp[-1:]

        while (
            first_symbol in "「『"
            and last_symbol in "」』"
            and ord(last_symbol) - ord(first_symbol) == 1  # 是同一对
        ):
            self.is_dialogue = True
            self.has_diag_symbol = True
            self.left_symbol = self.left_symbol + first_symbol
            self.right_symbol = last_symbol + self.right_symbol
            self.post_jp = self.post_jp[1:-1]  # 去首尾
            first_symbol, last_symbol = self.post_jp[:1], self.post_jp[-1:]

        # 情况2，一句话拆成2个的情况
        if self.next_tran != None:
            first_symbol_next = self.next_tran.post_jp[:1]
            last_symbol_next = self.next_tran.post_jp[-1:]
            if first_symbol == "「" and last_symbol != "」":
                if first_symbol_next != "「" and last_symbol_next == "」":
                    self.is_dialogue, self.next_tran.is_dialogue = True, True
                    self.has_diag_symbol, self.next_tran.has_diag_symbol = True, True
                    self.next_tran.speaker = self.speaker
                    self.left_symbol = self.left_symbol + first_symbol
                    self.next_tran.right_symbol = (
                        last_symbol_next + self.next_tran.right_symbol
                    )
                    self.post_jp, self.next_tran.post_jp = (
                        self.post_jp[1:],
                        self.next_tran.post_jp[:-1],
                    )

        # 情况3，一句话拆成3个的情况，一般不会再多了……
        if self.next_tran != None and self.next_tran.next_tran != None:
            first_symbol_next = self.next_tran.post_jp[:1]
            last_symbol_next = self.next_tran.post_jp[-1:]
            first_symbol_next_next = self.next_tran.next_tran.post_jp[:1]
            last_symbol_next_next = self.next_tran.next_tran.post_jp[-1:]
            if first_symbol == "「" and last_symbol != "」":
                if first_symbol_next != "「" and last_symbol_next != "」":
                    if first_symbol_next_next != "「" and last_symbol_next_next == "」":
                        (
                            self.is_dialogue,
                            self.next_tran.is_dialogue,
                            self.next_tran.next_tran.is_dialogue,
                        ) = (True, True, True)
                        (
                            self.has_diag_symbol,
                            self.next_tran.has_diag_symbol,
                            self.next_tran.next_tran.has_diag_symbol,
                        ) = (True, False, True)
                        self.next_tran.speaker, self.next_tran.next_tran.speaker = (
                            self.speaker,
                            self.speaker,
                        )
                        self.left_symbol = self.left_symbol + first_symbol
                        self.next_tran.next_tran.right_symbol = (
                            last_symbol_next_next
                            + self.next_tran.next_tran.right_symbol
                        )
                        self.post_jp, self.next_tran.next_tran.post_jp = (
                            self.post_jp[1:],
                            self.next_tran.next_tran.post_jp[:-1],
                        )

        self.post_jp = (dia_format if self.is_dialogue else mono_format).replace(
            "#句子", self.post_jp
        )

    def recover_dialogue_symbol(self):
        """
        译后用，对post_zh恢复对话符号，应该放在最后
        """
        self.post_zh = self.left_symbol + self.post_zh + self.right_symbol

    def some_normal_fix(self, line_break_symbol="\\n"):
        """
        译后用，一键应用常规的修复，要放在recover_dialogue_symbol前
        """
        if self.post_zh == "":
            return
        self.simple_fix_double_quotaion()
        self.remove_first_symbol(line_break_symbol)
        self.fix_last_symbol()

    def simple_fix_double_quotaion(self):
        """
        译后用，简单的记数法修复双引号左右不对称的问题，只适合句子里只有一对双引号的情况
        用在译后的字典替换后
        """
        if self.post_zh.count("”") == 2 and self.post_zh.count("“") == 0:
            self.post_zh = self.post_zh.replace("”", "“", 1)
        if self.post_zh.count("』") == 2 and self.post_zh.count("『") == 0:
            self.post_zh = self.post_zh.replace("』", "『", 1)

    def remove_first_symbol(self, line_break_symbol="\\n"):
        """译后用，移除第一个字符是逗号，句号，换行符的情况"""
        if self.post_zh[:1] in ["，", "。"]:
            self.post_zh = self.post_zh[1:]
        if self.post_zh[:2] in [line_break_symbol]:
            self.post_zh = self.post_zh[2:]

    def fix_last_symbol(self):
        """
        针对一些最后一个符号丢失的问题进行补回
        """
        if not self.pre_jp.endswith("\r\n") and self.post_zh.endswith("\r\n"):
            self.post_zh = self.post_zh[:-2]
        if self.post_jp[-1:] == "♪" and self.post_zh[-1:] != "♪":
            self.post_zh += "♪"
        if self.post_jp[-1:] != "、" and self.post_zh[-1:] == "，":
            self.post_zh = self.post_zh[:-1]
        if self.post_jp[-2:] == "！？" and self.post_zh[-1:] == "！":
            self.post_zh = self.post_zh + "？"
        if self.proofread_zh != "":
            if not self.pre_jp.endswith("\r\n") and self.proofread_zh.endswith("\r\n"):
                self.proofread_zh = self.proofread_zh[:-2]
            if self.post_jp[-1:] == "♪" and self.proofread_zh[-1:] != "♪":
                self.proofread_zh += "♪"
            if self.post_jp[-1:] != "、" and self.proofread_zh[-1:] == "，":
                self.proofread_zh = self.proofread_zh[:-1]
            if self.post_jp[-2:] == "！？" and self.post_zh[-1:] == "！":
                self.proofread_zh = self.proofread_zh + "？"

    def __replace_he2she(self):
        self.post_zh = self.post_zh.replace("他", "她").replace("其她", "其他")

    def fix_he2she(self, jp_name_list: List[str], zh_name_list: List[str]):
        """译后用，通过一些规则修复男女他的问题"""
        if self.post_zh == "":
            return
        if self.is_dialogue:
            self.fix_diag_he2she(jp_name_list, zh_name_list)
        else:
            self.fix_mono_he2she(jp_name_list, zh_name_list)

        for zh_name in zh_name_list:
            name_xs, name_xj = f"{zh_name}先生", f"{zh_name}小姐"
            if name_xs in self.post_zh:
                self.post_zh = self.post_zh.replace(name_xs, name_xj)
        pass

    def fix_diag_he2she(self, jp_name_list: List[str], zh_name_list: List[str]):
        """
        1、对话这一句包含女主角名
        """
        if self.is_dialogue == False:  # 不处理独白
            return

        # 1、对话这一句包含女主角名
        for her_name in zh_name_list:
            if her_name in self.post_zh:
                self.__replace_he2she()
                return

    def fix_mono_he2she(self, jp_name_list: List[str], zh_name_list: List[str]):
        """
        :jp_name_list:日文名列表，主要用于找speaker
        :zh_name_list:中文名列表，主要用于找内容
        :针对独白中男他的一些fix trick：
        :1、独白前一句的speaker是女主角的话
        :2、独白前一句是独白，内容包含女主角名，或包含她字的话
        :3、独白这一句里包含女主角名
        :4、独白下一句的speaker是女主角的话
        """
        if self.is_dialogue == True:  # 不处理对话
            return

        for her_name in zh_name_list:
            # 3、独白这一句里包含女主角名
            if her_name in self.post_zh:
                self.__replace_he2she()
                return

        pre_tran = self.prev_tran
        if pre_tran != None:
            # 1、独白前一句是对话，speaker是女主角的话
            if pre_tran.is_dialogue:
                if any(name in pre_tran.speaker for name in jp_name_list):
                    self.__replace_he2she()
                return

            # 2、独白往上找是独白，内容包含女主角名，或包含她字的话
            while pre_tran != None and pre_tran.is_dialogue == False:
                if "她" in pre_tran.post_zh:
                    self.__replace_he2she()
                    return
                else:
                    for her_name in zh_name_list:
                        if her_name in pre_tran.post_zh:
                            self.__replace_he2she()
                            return
                pre_tran = pre_tran.prev_tran  # 再往上找

        next_tran = self.next_tran
        if next_tran != None:
            # 4、独白下一句的speaker是女主角的话
            if next_tran.is_dialogue and next_tran.speaker in jp_name_list:
                self.__replace_he2she()
                return


CTransList = list[CSentense]
