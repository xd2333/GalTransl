#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from collections import Counter
from typing import List, Dict, Optional, Tuple
import zhconv

title="""
   ____       _ _____                    _ 
  / ___| __ _| |_   _| __ __ _ _ __  ___| |
 | |  _ / _` | | | || '__/ _` | '_ \/ __| |
 | |_| | (_| | | | || | | (_| | | | \__ \ |
  \____|\__,_|_| |_||_|  \__,_|_| |_|___/_|
                                           
  Core version: 1.0.1 [2023.05.23]
  Author: cx2333
"""

print(title)

class Translate:
    """
    每个Translate储存一句待翻译文本
    """

    def __init__(self, pre_jp: str, speaker: str = "", index=0) -> None:
        """每个Translate储存一句待翻译文本

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

        self.prev_tran: Translate = None  # 指向上一个tran
        self.next_tran: Translate = None  # 指向下一个tran

    def __repr__(self) -> str:
        tmp_post_jp = self.post_jp.replace("\r\n", "\\r\\n")
        tmp_post_zh = self.post_zh.replace("\r\n", "\\r\\n")
        tmp_proofread_zh = self.proofread_zh.replace("\r\n", "\\r\\n")
        char_t = "\t"
        return f"{self.index}: {tmp_post_jp}{char_t}{tmp_post_zh if self.proofread_zh == '' else tmp_proofread_zh}"

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


# List of Translate
TransList = List[Translate]


class BasicDicElement:
    """字典基本字元素"""

    conditionaDic_key = ["pre_jp", "post_jp", "pre_zh", "post_zh"]  # 条件字典
    situationsDic_key = ["mono", "diag"]  # 场景字典
    __slots__ = [
        "search_word",  # 搜索词
        "replace_word",  # 替换词
        "startswith_flag",  # 是否为startwith情况
        "special_key",  # 区分是否为特殊词典的关键字
        "is_situationsDic",  # 是否为情景字典
        "is_conditionaDic",  # 是否为条件字典
        "if_word_list",  # 条件字典中的条件词列表
        "spl_word",  # if_word_list的连接关键字
        "note",  # For GPT
    ]

    def __init__(
        self, search_word: str = "", replace_word: str = "", special_key: str = ""
    ) -> None:
        self.search_word: str = search_word
        self.replace_word: str = replace_word

        self.startswith_flag: bool = False
        if search_word.startswith("^^"):  # startswith情况
            self.startswith_flag = True
            self.search_word = search_word[2:]

        self.special_key: str = special_key  # 区分是否为特殊词典的关键字

        self.is_situationsDic: bool = False

        self.is_conditionaDic: bool = False
        self.if_word_list: List[ifWord] = None  # 条件字典中的条件词列表
        self.spl_word: str = ""  # if_word_list的连接关键字

    def __repr__(self) -> str:
        return f"{self.search_word} -> {self.replace_word}"

    def load_line(self, line: str, type="Normal"):
        """
        :line: 一行
        """
        if line.startswith("\n"):
            return
        elif line.startswith("\\\\") or line.startswith("//"):  # 注释行跳过
            return
        sp = line.rstrip("\r\n").split("\t")  # 去多余换行符，Tab分割
        len_sp = len(sp)
        if len_sp < 2:  # 至少是2个元素
            return None

        is_conditionaDic_line = True if sp[0] in self.conditionaDic_key else False
        is_situationsDic_line = True if sp[0] in self.situationsDic_key else False
        if is_conditionaDic_line:
            self.is_conditionaDic = True
            if_word = sp[1]
            spl_word = "[and]" if "[and]" in if_word else "[or]"  # 判断连接字符
            # 初始化ifWord的list
            self.special_key = sp[0]
            self.if_word_list = [ifWord(w.strip()) for w in if_word.split(spl_word)]
            self.spl_word = spl_word
            self.search_word = sp[2]

        if self.search_word.startswith("^^"):  # startswith情况
            self.startswith_flag = True
            self.search_word = self.search_word[2:]


class ifWord:
    __slots__ = ["without_flag", "startswith_flag", "endswith_flag", "word"]

    def __init__(self, if_word):
        if if_word.startswith(">"):
            startswith_flag, if_word = True, if_word[1:]
        else:
            startswith_flag = False

        if if_word.endswith("<"):
            endswith_flag, if_word = True, if_word[:-1]
        else:
            endswith_flag = False

        if if_word.startswith("!"):
            without_flag, if_word = True, if_word[1:]
        else:
            without_flag = False

        self.without_flag = without_flag
        self.startswith_flag = startswith_flag
        self.endswith_flag = endswith_flag
        self.word = if_word


class NormalDic:
    """
    :由多个BasicDic字典元素构成的大字典List（这个Dic不Normal但是懒得改名）
    :dic_list:字典文件的list，可以只有文件名，然后提供dir参数，也可以是完整的，混搭也可以
    :dic_base_dir:字典目录的path，会自动进行拼接
    """

    conditionaDic_key = ["pre_jp", "post_jp", "pre_zh", "post_zh"]  # 条件字典
    situationsDic_key = ["mono", "diag"]  # 场景字典

    def __init__(self, dic_list: list, dic_base_dir: str = "") -> None:
        self.dic_list: List[BasicDicElement] = []
        if dic_base_dir != "":
            dic_list = self.dic_auto_make_path(dic_list, dic_base_dir)
        for dic_path in dic_list:
            self.load_dic(dic_path)  # 加载字典

    def dic_auto_make_path(self, dic_name_list: List[str], dic_dir: str):
        for i, dic_name in enumerate(dic_name_list):
            if "\\" not in dic_name:
                dic_name_list[i] = os.path.join(dic_dir, dic_name)
        return dic_name_list

    def load_dic(self, dic_path: str):
        """加载一个字典txt到这个对象的内存"""
        if not os.path.exists(dic_path):
            print(f"{dic_path}不存在，请检查路径。")
            return
        with open(dic_path, encoding="utf8") as f:
            dic_lines = f.readlines()
        if len(dic_lines) == 0:
            return

        normalDic_count = 0
        conditionaDic_count = 0
        situationsDic_count = 0

        for line in dic_lines:
            if line.startswith("\n"):
                continue
            elif line.startswith("\\\\") or line.startswith("//"):  # 注释行跳过
                continue

            sp = line.rstrip("\r\n").split("\t")  # 去多余换行符，Tab分割
            len_sp = len(sp)
            if len_sp < 2:  # 至少是2个元素
                continue

            is_conditionaDic_line = True if sp[0] in self.conditionaDic_key else False
            is_situationsDic_line = True if sp[0] in self.situationsDic_key else False
            if (is_conditionaDic_line and len_sp < 4) or (
                is_situationsDic_line and len_sp < 3
            ):
                continue

            if is_conditionaDic_line:
                if_word = sp[1]
                spl_word = "[and]" if "[and]" in if_word else "[or]"  # 判断连接字符
                # 初始化ifWord的list
                if_word_list = [ifWord(w.strip()) for w in if_word.split(spl_word)]
                con_dic = BasicDicElement(sp[2], sp[3], sp[0])
                con_dic.is_conditionaDic = True
                con_dic.if_word_list = if_word_list
                con_dic.spl_word = spl_word
                self.dic_list.append(con_dic)
                conditionaDic_count += 1
            elif is_situationsDic_line:
                sit_dic = BasicDicElement(sp[1], sp[2], sp[0])
                sit_dic.is_situationsDic = True
                self.dic_list.append(sit_dic)
                situationsDic_count += 1
            else:
                self.dic_list.append(BasicDicElement(sp[0], sp[1]))
                normalDic_count += 1
        print(
            "载入 "
            + os.path.basename(dic_path)
            + "  "
            + (str(normalDic_count) + "普通；" if normalDic_count != 0 else "")
            + (str(conditionaDic_count) + "条件；" if conditionaDic_count != 0 else "")
            + (str(situationsDic_count) + "场景；" if situationsDic_count != 0 else "")
        )

    def do_replace(self, input_text: str, input_tran: Translate) -> str:
        """
        通过这个dic字典来优化一个句子。
        input_text：要被润色的句子
        input_translate：这个句子所在的Translate对象
        """
        # 遍历每个BasicDicElement做替换
        for dic in self.dic_list:
            # 场景字典判断
            if dic.is_situationsDic:
                if ("diag" == dic.special_key and input_tran.is_dialogue == False) or (
                    "mono" == dic.special_key and input_tran.is_dialogue == True
                ):
                    continue
            # 条件字典屎山
            if dic.is_conditionaDic:
                can_replace = False  # True代表本轮满足替换条件
                # 取对应的查找关键字的句子
                find_ifword_text: str = vars(input_tran)[dic.special_key]
                # 遍历if_word_list
                for if_word in dic.if_word_list:
                    # 因为如果有stratwith的话需要修改word，所以要新建一份副本
                    if_word_now = if_word.word
                    if if_word_now == "":
                        continue
                    if if_word.startswith_flag:
                        if dic.special_key == "pre_jp":
                            # 把left_symbol先拼接回去
                            if_word_now = input_tran.left_symbol + if_word_now
                        elif dic.special_key == "post_jp":
                            # 需要给判断词加上对应的format
                            if input_tran.is_dialogue:
                                if_word_now = (
                                    input_tran.dia_format.split("#句子")[0] + if_word_now
                                )
                            else:
                                if_word_now = (
                                    input_tran.mono_format.split("#句子")[0] + if_word_now
                                )

                    if if_word_now in ["~", "(同上)", "（同上）"]:  # 同上flag判断
                        can_replace = True if last_one_success == True else False
                    elif if_word.startswith_flag:  # startswith
                        can_replace = find_ifword_text.startswith(if_word_now)
                    else:  # 默认为find
                        can_replace = if_word_now in find_ifword_text

                    if if_word.without_flag:  # 有without_flag时则取反
                        can_replace = not can_replace

                    # and中有一个是False就跳出
                    if dic.spl_word == "[and]" and can_replace == False:
                        break
                    elif (
                        dic.spl_word == "[or]" and can_replace == True
                    ):  # or中有一个是True就跳出
                        break

                if not can_replace:  # 条件不满足，跳到字典下一条
                    last_one_success = False
                    continue
                else:
                    last_one_success = True

            # 不管是不是特殊字典，替换部分都是一样的，跑到这里就是条件满足了：

            search_word = dic.search_word
            replace_word = dic.replace_word

            # 但是需要检查search_word是否是startwith情况
            if dic.startswith_flag:
                len_search_word = len(search_word)
                len_input_text = len(input_text)
                if len_search_word > len_input_text:
                    continue  # 肯定不满足
                elif input_text[:len_search_word] == search_word:
                    input_text = input_text.replace(search_word, replace_word, 1)
            else:  # 普通情况
                input_text = input_text.replace(search_word, replace_word)

        return input_text


class GptDict:
    conditionaDic_key = ["pre_jp", "post_jp", "pre_zh", "post_zh"]  # 条件字典关键字

    def __init__(self, dic_list: list, dic_base_dir: str = "") -> None:
        self._dic_list: List[BasicDicElement] = []
        if dic_base_dir != "":
            dic_list = self.dic_auto_make_path(dic_list, dic_base_dir)
        for dic_path in dic_list:
            self.load_dic(dic_path)  # 加载字典

    def dic_auto_make_path(self, dic_name_list: List[str], dic_dir: str):
        for i, dic_name in enumerate(dic_name_list):
            if "\\" not in dic_name:
                dic_name_list[i] = os.path.join(dic_dir, dic_name)
        return dic_name_list

    def load_dic(self, dic_path: str):
        """加载一个字典txt到这个对象的内存"""
        if not os.path.exists(dic_path):
            print(f"{dic_path}不存在，请检查路径。")
            return
        with open(dic_path, encoding="utf8") as f:
            dic_lines = f.readlines()
        if len(dic_lines) == 0:
            return

        normalDic_count = 0

        for line in dic_lines:
            if line.startswith("\n"):
                continue
            elif line.startswith("\\\\") or line.startswith("//"):  # 注释行跳过
                continue

            sp = line.rstrip("\r\n").split("\t")  # 去多余换行符，Tab分割
            len_sp = len(sp)

            if len_sp < 2:  # 至少是2个元素
                continue

            # 条件字典判断
            is_conditionaDic_line = True if sp[0] in self.conditionaDic_key else False
            if is_conditionaDic_line and len_sp < 4:
                continue

            dic = BasicDicElement(sp[0], sp[1])
            if len_sp > 2 and sp[2] != None:
                dic.note = sp[2]
            else:
                dic.note = ""
            self._dic_list.append(dic)
            normalDic_count += 1
        print(f"载入 GPT字典: {os.path.basename(dic_path)} {normalDic_count}个词条")

    def gen_prompt(self, trans_list: List[Translate]):
        promt = ""
        for dic in self._dic_list:
            if dic.startswith_flag or dic.search_word in "\n".join(
                [f"{tran.speaker}:{tran.post_jp}" for tran in trans_list]
            ):
                promt += f"| {dic.search_word} | {dic.replace_word} |"
                if dic.note != "":
                    promt += f" {dic.note}"
                promt += " |\n"

        if promt != "":
            promt = (
                "# Glossary\n| Src | Dst(/Dst2/..) | Note |\n| --- | --- | --- |\n"
                + promt
            )
        return promt


def load_transList_from_json_jp(json_str_or_list):
    """
    从json文件路径、json字符串、json list中载入待翻译列表
    json格式为[{"name":xx/"names":[],"message/pre_jp":"xx"},...]
    """
    trans_list: TransList = []

    if isinstance(json_str_or_list, str):
        if os.path.exists(json_str_or_list):
            with open(json_str_or_list, "r", encoding="utf8") as f:
                json_str_or_list = f.read()
        json_list = json.loads(json_str_or_list)
    elif isinstance(json_str_or_list, list):
        json_list = json_str_or_list

    for i, item in enumerate(json_list):
        name = (
            item["name"] if "name" in item else item["names"] if "names" in item else ""
        )
        pre_jp = (
            item["message"]
            if "message" in item
            else item["pre_jp"]
            if "pre_jp" in item
            else ""
        )
        index = item["index"] if "index" in item else i + 1
        tmp_tran = Translate(pre_jp, name, index)
        # 链接上下文
        if trans_list != []:
            tmp_tran.prev_tran = trans_list[-1]
            trans_list[-1].next_tran = tmp_tran
        trans_list.append(tmp_tran)

    return trans_list


def save_transList_to_json_cn(trans_list: TransList, save_path: str, name_dict={}):
    result_list = []
    for tran in trans_list:
        if tran._speaker != "":
            if type(tran._speaker) == list:
                result_name = []
                for name in tran._speaker:
                    result_name.append(name_dict[name] if name in name_dict else name)
                result_list.append({"names": result_name, "message": tran.post_zh})
            else:
                result_name = (
                    name_dict[tran._speaker]
                    if tran._speaker in name_dict
                    else tran._speaker
                )
                result_list.append({"name": result_name, "message": tran.post_zh})
        else:
            result_list.append({"message": tran.post_zh})
    with open(save_path, "w", encoding="utf8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=4)


def load_trans_from_file(jp_txt_path: str, encode="utf8"):
    """(废弃)从标准txt_jp文件载入translist，标准行定义:★✰index_key【speaker】✰★pre_jp

    Args:
        jp_txt_path (str): 日文txt文件路径
        encode (str): 文件编码

    Returns:
        TransList: 由Translate对象组成的list
    """
    with open(jp_txt_path, encoding=encode) as f:
        jp_lines = f.readlines()

    trans_list: TransList = []

    for i, jp_text in enumerate(jp_lines):
        pre_jp = get_mid_string(jp_text, "✰★\t", "\n")
        if pre_jp is None:
            continue
        param = get_mid_string(jp_text, "★✰", "✰★")
        index_key = param if "【" not in param else param[: param.find("【")]
        if index_key == "":
            index_key = i
        else:
            index_key = int(index_key)
        speaker = get_mid_string(param, "【", "】") if "【" in param else ""
        tmpTran = Translate(pre_jp, speaker, index_key)
        if trans_list:  # trans_list不为空
            tmpTran.prev_tran = trans_list[-1]
            trans_list[-1].next_tran = tmpTran

        trans_list.append(tmpTran)

    return trans_list


def save_json_jp_to_txt_jp(jp_list, txt_jp_path):
    """jp_list格式为[{"name":xx,"message":xx},...]"""
    with open(txt_jp_path, "w", encoding="utf8") as f:
        for i, jp in enumerate(jp_list):
            name = jp["name"] if "name" in jp else ""
            f.write(f"★✰{i+1}【{name}】✰★\t{jp['message']}\n")


def save_trans_list_to_file(
    trans_list: TransList,
    save_path: str,
    encode: str = "utf8",
    split_symbol: str = "\t",
    with_speaker: bool = False,
):
    """（废弃）保存translist到文件

    Args:
        trans_list (TransList): translist
        save_path (str): 保存路径
        encode (str, optional): 保存编码. Defaults to "utf8".
        split_symbol (str, optional): 分割文本. Defaults to "\\t".
    """
    with open(save_path, encoding=encode, mode="w") as f:
        if with_speaker:
            f.writelines(
                [
                    f"{t._speaker}{split_symbol}{t.pre_jp}{split_symbol}{t.post_zh}\n"
                    for t in trans_list
                ]
            )
        else:
            f.writelines([f"{t.pre_jp}{split_symbol}{t.post_zh}\n" for t in trans_list])


def get_trans_cache_from_file(
    trans_list: List[Translate], cache_file_path, unhit_flag="", proofread=False
):
    """
    （废弃）通过一个cache文件，避免无意义的重新翻译，大幅提高速度
    cacheFile定义：前原➤➤前润➤➤后原
    主要检查新前润是否有变化，返回trans_list_hit、trans_list_unhit
    """
    cache_dict = {}
    trans_list_hit = []
    trans_list_unhit = []
    have_mono_flag = False  # 新版cache格式flag
    if not os.path.exists(cache_file_path):
        return [], trans_list

    with open(cache_file_path, encoding="utf8") as f:
        for line in f.readlines():
            sp = line.rstrip("\r\n").split("➤➤")
            if len(sp) < 3:
                continue
            cache_dict[sp[0]] = [sp[1], sp[2]]

    if len(cache_dict) == 0:
        return [], trans_list

    # 判断是否为带对话标志的格式
    if "★✰" in next(iter(cache_dict.keys())):  # 取dict第一个key的trick
        have_mono_flag = True

    for tran in trans_list:
        tran_key = tran.pre_jp
        if have_mono_flag:
            tran_key = (
                "★✰{}✰★".format("diag" if tran.is_dialogue else "mono") + tran_key
            )

        if tran_key not in cache_dict:  # 原句不在缓存
            trans_list_unhit.append(tran)
            continue
        if tran.post_jp != cache_dict[tran_key][0]:  # 前润被改变
            trans_list_unhit.append(tran)
            continue
        # 后原为空
        if cache_dict[tran_key][1] == "":
            trans_list_unhit.append(tran)
            continue
        # 后原存在unhit_flag
        if unhit_flag != "" and unhit_flag in cache_dict[tran_key][1]:
            trans_list_unhit.append(tran)
            continue
        # 剩下的都是击中缓存的,post_zh初始值赋pre_zh
        tran.pre_zh = zhconv.convert(cache_dict[tran_key][1], "zh-cn")
        # 转换为简体
        tran.post_zh = tran.pre_zh

        if proofread:
            tran.has_proofread = True
        trans_list_hit.append(tran)

    return trans_list_hit, trans_list_unhit


def get_transCache_from_json(
    trans_list: List[Translate], cache_file_path, retry_failed=False, proofread=False
):
    if not os.path.exists(cache_file_path):
        return [], trans_list

    trans_list_hit = []
    trans_list_unhit = []
    with open(cache_file_path, encoding="utf8") as f:
        cache_dictList = json.load(f)

    cache_dict = {cache["index"]: cache for cache in cache_dictList}

    for tran in trans_list:
        if tran.index not in cache_dict:  # 原句不在缓存
            trans_list_unhit.append(tran)
            continue
        if tran.post_jp != cache_dict[tran.index]["post_jp"]:  # 前润被改变
            trans_list_unhit.append(tran)
            continue
        if (
            "pre_zh" not in cache_dict[tran.index]
            or cache_dict[tran.index]["pre_zh"] == ""
        ):  # 后原为空
            trans_list_unhit.append(tran)
            continue
        # 重试失败的
        if retry_failed and "Failed translation" in cache_dict[tran.index]["pre_zh"]:
            if cache_dict[tran.index]["proofread_zh"] == "":  # 且未校对
                trans_list_unhit.append(tran)
                continue

        # 剩下的都是击中缓存的,post_zh初始值赋pre_zh
        tran.pre_zh = cache_dict[tran.index]["pre_zh"]
        if "trans_by" in cache_dict[tran.index]:
            tran.trans_by = cache_dict[tran.index]["trans_by"]
        if "proofread_zh" in cache_dict[tran.index]:
            tran.proofread_zh = cache_dict[tran.index]["proofread_zh"]
        if "proofread_by" in cache_dict[tran.index]:
            tran.proofread_by = cache_dict[tran.index]["proofread_by"]
        if "trans_conf" in cache_dict[tran.index]:
            tran.trans_conf = cache_dict[tran.index]["trans_conf"]
        if "doub_content" in cache_dict[tran.index]:
            tran.doub_content = cache_dict[tran.index]["doub_content"]
        if "unknown_proper_noun" in cache_dict[tran.index]:
            tran.unknown_proper_noun = cache_dict[tran.index]["unknown_proper_noun"]
        if "problem" in cache_dict[tran.index]:
            tran.problem = cache_dict[tran.index]["problem"]

        if tran.proofread_zh != "":
            tran.post_zh = tran.proofread_zh
        else:
            tran.post_zh = tran.pre_zh

        if proofread and tran.proofread_zh == "":
            trans_list_unhit.append(tran)
            continue

        trans_list_hit.append(tran)

    return trans_list_hit, trans_list_unhit


def save_transCache_to_json(
    trans_list: List[Translate], cache_file_path, proofread=False
):
    cache_json = []

    for tran in trans_list:
        if tran.pre_zh == "":
            continue

        cache_obj = {
            "index": tran.index,
            "name": tran._speaker,
            "pre_jp": tran.pre_jp,
            "post_jp": tran.post_jp,
            "pre_zh": tran.pre_zh,
        }

        cache_obj["proofread_zh"] = tran.proofread_zh

        if tran.problem != "":
            cache_obj["problem"] = tran.problem

        cache_obj["trans_by"] = tran.trans_by
        cache_obj["proofread_by"] = tran.proofread_by

        if tran.trans_conf != 0:
            cache_obj["trans_conf"] = tran.trans_conf
        if tran.doub_content != "":
            cache_obj["doub_content"] = tran.doub_content
        if tran.unknown_proper_noun != "":
            cache_obj["unknown_proper_noun"] = tran.unknown_proper_noun
        cache_json.append(cache_obj)

    with open(cache_file_path, mode="w", encoding="utf8") as f:
        json.dump(cache_json, f, ensure_ascii=False, indent=4)


def save_trans_cache_to_file(
    trans_list: List[Translate], cache_file_path, proofread=False
):
    """(废弃)保存trans_list到cache文件，新定义为★✰mono/diag✰★pre_jp➤➤post_jp➤➤pre_zh

    Args:
        trans_list (List[Translate]): translist
        cache_file_path (str): 文件路径
    """

    txt_list = []
    for tran in trans_list:
        if tran.pre_zh == "":
            continue
        if proofread and not tran.has_proofread:  # 如果是校对模式，只保存校对过的
            continue
        sen_type = "diag" if tran.is_dialogue else "mono"
        txt_list.append(f"★✰{sen_type}✰★{tran.pre_jp}➤➤{tran.post_jp}➤➤{tran.pre_zh}\n")
    with open(cache_file_path, mode="w", encoding="utf8") as f:
        f.writelines(txt_list)


def get_most_common_char(input_text: str) -> Tuple[str, int]:
    """
    此函数接受一个字符串作为输入，并返回该字符串中最常见的字符及其出现次数。
    它会忽略黑名单中的字符，包括 "." 和 "，"。

    参数:
    - input_text: 一段文本字符串。

    返回值:
    - 包含最常见字符及其出现次数的元组。
    """
    black_list: List[str] = [".", "，"]
    counter: Counter = Counter(input_text)
    most_common = counter.most_common()
    most_char: str = ""
    most_char_count: int = 0
    for char in most_common:
        if char[0] not in black_list:
            most_char = char[0]
            most_char_count = char[1]
            break
    return most_char, most_char_count


def get_mid_string(text: str, start_str: str, end_str: str) -> Optional[str]:
    """
    此函数从 `text` 中提取出出现在 `start_str` 和 `end_str` 之间的子字符串。

    参数:
    - text: 要搜索子字符串的字符串。
    - start_str: 子字符串的起始字符串。
    - end_str: 子字符串的结束字符串。

    返回值:
    - 如果 `text` 中存在子字符串，则返回包含子字符串的字符串，否则返回 None。
    """
    start: int = text.find(start_str)
    if start >= 0:
        start += len(start_str)
        end: int = text.find(end_str, start)
        if end >= 0:
            return text[start:end].strip()
    return None


def find_problems(trans_list: List[Translate], find_type=[], arinashi_dict={}) -> None:
    """
    此函数接受一个翻译列表，查找其中的问题并将其记录在每个翻译对象的 `problem` 属性中。

    参数:
    - trans_list: 翻译对象列表。
    - find_type: 要查找的问题类型列表。
    - arinashi_dict: 包含本文中的日文单词和其对应中文翻译的字典。

    返回值:
    - 无返回值，但会修改每个翻译对象的 `problem` 属性。
    """
    for tran in trans_list:
        find_from_str = tran.post_zh
        problem_list = []
        if "词频过高" in find_type:
            most_word, word_count = get_most_common_char(find_from_str)
            if word_count > 20 and most_word != ".":
                problem_list.append(f"词频过高-'{most_word}'{str(word_count)}次")
        if "本无括号" in find_type:
            if "（" not in tran.pre_jp and (
                "（" in find_from_str or ")" in find_from_str
            ):
                problem_list.append("本无括号")
        if "本无引号" in find_type:
            if "『" not in tran.post_jp and "「" not in tran.post_jp:
                if "‘" in find_from_str or "“" in find_from_str:
                    problem_list.append("本无引号")
        if "残留日文" in find_type:
            if contains_japanese(find_from_str):
                problem_list.append("残留日文")
        if "丢失换行" in find_type:
            if tran.pre_jp.count("\r\n") > find_from_str.count("\r\n"):
                problem_list.append("丢失换行")
        if "多加换行" in find_type:
            if tran.pre_jp.count("\r\n") < find_from_str.count("\r\n"):
                problem_list.append("多加换行")
        if "比日文长" in find_type:
            if len(find_from_str) > len(tran.pre_jp) * 1.2:
                problem_list.append(
                    f"比日文长{round(len(find_from_str)/len(tran.pre_jp),1)}倍"
                )
        if "彩云不识" in find_type:
            if "some" in tran.pre_zh or "SOME" in tran.pre_zh:
                problem_list.append("彩云不识")
        if arinashi_dict != {}:
            for key, value in arinashi_dict.items():
                if key not in tran.pre_jp and value in find_from_str:
                    problem_list.append(f"本无 {key} 译有 {value}")
                if key in tran.pre_jp and value not in find_from_str:
                    problem_list.append(f"本有 {key} 译无 {value}")

        if problem_list:
            tran.problem = ",".join(problem_list)
        else:
            tran.problem = ""


def find_problem_save_log(
    trans_list: List[Translate],
    file_name: str,
    save_path: str,
    mono_flag_list=[],
    diag_flag_list=[],
):
    """
    (废弃)从trans_list里发现问题并记录日志到save_path文件
    """
    problem_log_list = []  # 搜集问题句
    for tran in trans_list:
        most_word, word_count = get_most_common_char(
            tran.pre_zh
        )  # 要用pre来统计，因为post可能过滤掉
        if word_count > 20 and most_word != ".":
            problem_log_list.append(
                f"➤➤词频过高：{file_name}，高频词：{most_word}，{str(word_count)}次\n{tran.pre_jp}|{tran.post_zh}\n"
            )
        if "（" not in tran.pre_jp and ("（" in tran.post_zh or ")" in tran.post_zh):
            problem_log_list.append(
                f"➤➤本无括号： {file_name}：\n{tran.pre_jp}|{tran.post_zh}\n"
            )
        if (
            "some" in tran.pre_zh
            or "SOME" in tran.pre_zh
            or (tran.post_zh == "" and tran.pre_jp != "")
            or tran.post_jp == "「」"
        ):
            problem_log_list.append(
                f"➤➤彩云不识：{file_name} ：\n{tran.pre_jp}\n{tran.post_zh}\n"
            )
        if contains_japanese(tran.post_zh):
            problem_log_list.append(
                f"➤➤日文：{file_name} ：\n{tran.pre_jp}\n{tran.post_zh}\n"
            )
        if "\\r\\n" in tran.pre_jp and "\\r\\n" not in tran.post_zh:
            problem_log_list.append(
                f"➤➤换行丢失：{file_name} ：\n{tran.pre_jp}\n{tran.post_zh}\n"
            )
        for flag in mono_flag_list:
            if tran.speaker == "" and flag in tran.post_zh:
                problem_log_list.append(
                    f"➤➤mono特殊标记'{flag}'：{file_name} ：\n{tran.pre_jp}\n{tran.post_zh}\n"
                )
        for flag in diag_flag_list:
            if tran.speaker != "" and flag in tran.post_zh:
                problem_log_list.append(
                    f"➤➤diag特殊标记'{flag}'：{file_name} ：\n{tran.pre_jp}\n{tran.post_zh}\n"
                )
    if (len(problem_log_list)) != 0:
        with open(save_path, mode="w", encoding="utf8") as f:
            f.writelines(problem_log_list)
    else:
        if os.path.exists(save_path):
            os.remove(save_path)


def contains_japanese(text: str) -> bool:
    """
    此函数接受一个字符串作为输入，检查其中是否包含日文字符。

    参数:
    - text: 要检查的字符串。

    返回值:
    - 如果字符串中包含日文字符，则返回 True，否则返回 False。
    """
    # 日文字符范围
    hiragana_range = (0x3040, 0x309F)
    katakana_range = (0x30A0, 0x30FF)
    hankaku_range = (0xFF66, 0xFF9F)

    # 检查字符串中的每个字符
    for char in text:
        # 排除ー
        if char in ["ー", "・"]:
            continue
        # 获取字符的 Unicode 码点
        code_point = ord(char)
        # 检查字符是否在日文字符范围内
        if (
            hiragana_range[0] <= code_point <= hiragana_range[1]
            or katakana_range[0] <= code_point <= katakana_range[1]
            or hankaku_range[0] <= code_point <= hankaku_range[1]
        ):
            return True
    return False


def load_name_table(name_table_path: str) -> Dict[str, str]:
    """
    This function loads the name table from the given path.

    Args:
    - name_table_path: The path to the name table.

    Returns:
    - A dictionary containing the name table.
    """
    import csv

    name_table: Dict[str, str] = {}
    with open(name_table_path, mode="r", encoding="utf8") as f:
        reader = csv.reader(f)
        # Skip the header
        next(reader)
        for row in reader:
            name_table[row[0]] = row[1]
    return name_table

def extract_code_blocks(content):
    # 匹配带语言标签的代码块
    pattern_with_lang = re.compile(r'```([\w]*)\n([\s\S]*?)\n```')
    matches_with_lang = pattern_with_lang.findall(content)

    # 提取所有匹配到的带语言标签的代码块
    lang_list = []
    code_list = []
    for match in matches_with_lang:
        lang_list.append(match[0])
        code_list.append(match[1])

    return lang_list, code_list

if __name__ == "__main__":
    pass
