"""
分析问题
"""
from GalTransl.CSentense import CSentense, CTransList
from GalTransl.StringUtils import get_most_common_char, contains_japanese
from typing import List
from os.path import exists as isPathExists
from os import remove as rm
from enum import Enum


class CTranslateProblem(Enum):
    """
    问题类型
    """

    词频过高 = 1
    本无括号 = 2
    本无引号 = 3
    残留日文 = 4
    丢失换行 = 5
    多加换行 = 6
    比日文长 = 7
    彩云不识 = 8


def find_problems(
    trans_list: CTransList, find_type: list[CTranslateProblem] = [], arinashi_dict={}
) -> None:
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
        if CTranslateProblem.词频过高 in find_type:
            most_word, word_count = get_most_common_char(find_from_str)
            if word_count > 20 and most_word != ".":
                problem_list.append(f"词频过高-'{most_word}'{str(word_count)}次")
        if CTranslateProblem.本无括号 in find_type:
            if "（" not in tran.pre_jp and (
                "（" in find_from_str or ")" in find_from_str
            ):
                problem_list.append("本无括号")
        if CTranslateProblem.本无引号 in find_type:
            if "『" not in tran.post_jp and "「" not in tran.post_jp:
                if "‘" in find_from_str or "“" in find_from_str:
                    problem_list.append("本无引号")
        if CTranslateProblem.残留日文 in find_type:
            if contains_japanese(find_from_str):
                problem_list.append("残留日文")
        if CTranslateProblem.丢失换行 in find_type:
            if tran.pre_jp.count("\r\n") > find_from_str.count("\r\n"):
                problem_list.append("丢失换行")
        if CTranslateProblem.多加换行 in find_type:
            if tran.pre_jp.count("\r\n") < find_from_str.count("\r\n"):
                problem_list.append("多加换行")
        if CTranslateProblem.比日文长 in find_type:
            if len(find_from_str) > len(tran.pre_jp) * 1.2:
                problem_list.append(
                    f"比日文长{round(len(find_from_str)/len(tran.pre_jp),1)}倍"
                )
        if CTranslateProblem.彩云不识 in find_type:
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
    trans_list: CTransList,
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
        if isPathExists(save_path):
            rm(save_path)
