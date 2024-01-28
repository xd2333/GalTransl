"""
分析问题
"""
from GalTransl.CSentense import CTransList
from GalTransl.Utils import get_most_common_char, contains_japanese
from GalTransl.Dictionary import CGptDict
from enum import Enum


class CTranslateProblem(Enum):
    """
    问题类型
    """

    词频过高 = 1
    标点错漏 = 2
    本无括号 = 2
    本无引号 = 2
    残留日文 = 3
    丢失换行 = 4
    多加换行 = 5
    比日文长 = 6
    字典使用 = 7


def find_problems(
    trans_list: CTransList,
    find_type: list[CTranslateProblem] = [],
    arinashi_dict={},
    gpt_dict: CGptDict = None,
) -> None:
    """
    此函数接受一个翻译列表，查找其中的问题并将其记录在每个翻译对象的 `problem` 属性中。

    参数:
    - trans_list: 翻译对象列表。
    - find_type: 要查找的问题类型列表。
    - arinashi_dict: 一个自定义字典，其中的键值对将会被用于查找问题。

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
        if CTranslateProblem.标点错漏 in find_type:
            char_to_error = {
                ("（", ")"): "括号",
                "：": "冒号",
                "*": "*号",
                ("『", "「", "“"): "引号",
            }

            for chars, error in char_to_error.items():
                if isinstance(chars, tuple):
                    if not any(char in tran.pre_jp for char in chars):
                        if any(char in find_from_str for char in chars):
                            problem_list.append(f"本无{error}")
                    elif any(char in tran.pre_jp for char in chars):
                        if not any(char in find_from_str for char in chars):
                            problem_list.append(f"本有{error}")
                else:
                    if chars not in tran.pre_jp:
                        if chars in find_from_str:
                            problem_list.append(f"本无{error}")
                    elif chars in tran.pre_jp:
                        if chars not in find_from_str:
                            problem_list.append(f"本有{error}")
        if CTranslateProblem.残留日文 in find_type:
            if contains_japanese(find_from_str):
                problem_list.append("残留日文")
        if CTranslateProblem.丢失换行 in find_type:
            if tran.pre_jp.count("\n") > find_from_str.count("\n"):
                problem_list.append("丢失换行")
        if CTranslateProblem.多加换行 in find_type:
            if tran.pre_jp.count("\n") < find_from_str.count("\n"):
                problem_list.append("多加换行")
        if CTranslateProblem.比日文长 in find_type:
            if len(find_from_str) > len(tran.pre_jp) * 1.3:
                problem_list.append(
                    f"比日文长{round(len(find_from_str)/max(len(tran.pre_jp),0.1),1)}倍"
                )
        if CTranslateProblem.字典使用 in find_type:
            if val := gpt_dict.check_dic_use(find_from_str, tran):
                problem_list.append(val)
        if arinashi_dict != {}:
            for key, value in arinashi_dict.items():
                if key not in tran.pre_jp and value in find_from_str:
                    problem_list.append(f"本无 {key} 译有 {value}")
                if key in tran.pre_jp and value not in find_from_str:
                    problem_list.append(f"本有 {key} 译无 {value}")

        if problem_list:
            tran.problem = ", ".join(problem_list)
        else:
            tran.problem = ""
