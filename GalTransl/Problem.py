"""
分析问题
"""
from GalTransl.CSentense import CTransList
from GalTransl.ConfigHelper import CProjectConfig, CProblemType
from GalTransl.Utils import get_most_common_char, contains_japanese
from GalTransl.Dictionary import CGptDict


def find_problems(
    trans_list: CTransList,
    projectConfig: CProjectConfig,
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
    arinashi_dict = projectConfig.getProblemAnalyzeArinashiDict()
    find_type = projectConfig.getProblemAnalyzeConfig("problemList")
    if not find_type:
        find_type = projectConfig.getProblemAnalyzeConfig("GPT35")  # 兼容旧版
    lb_symbol = projectConfig.getlbSymbol()

    for tran in trans_list:
        pre_jp = tran.pre_jp
        post_jp = tran.post_jp
        pre_zh = tran.pre_zh
        post_zh = tran.post_zh

        problem_list = []
        if CProblemType.词频过高 in find_type:
            most_word, word_count = get_most_common_char(post_zh)
            if word_count > 20 and most_word != ".":
                problem_list.append(f"词频过高-'{most_word}'{str(word_count)}次")
        if CProblemType.标点错漏 in find_type:
            char_to_error = {
                ("（", ")"): "括号",
                "：": "冒号",
                "*": "*号",
                ("『", "「", "“"): "引号",
            }

            for chars, error in char_to_error.items():
                if isinstance(chars, tuple):
                    if not any(char in pre_jp for char in chars):
                        if any(char in post_zh for char in chars):
                            problem_list.append(f"本无{error}")
                    elif any(char in pre_jp for char in chars):
                        if not any(char in post_zh for char in chars):
                            problem_list.append(f"本有{error}")
                else:
                    if chars not in pre_jp:
                        if chars in post_zh:
                            problem_list.append(f"本无{error}")
                    elif chars in pre_jp:
                        if chars not in post_zh:
                            problem_list.append(f"本有{error}")
        if CProblemType.残留日文 in find_type:
            if contains_japanese(post_zh):
                problem_list.append("残留日文")
        if CProblemType.丢失换行 in find_type:
            if pre_jp.count(lb_symbol) > post_zh.count(lb_symbol):
                problem_list.append("丢失换行")
        if CProblemType.多加换行 in find_type:
            if pre_jp.count(lb_symbol) < post_zh.count(lb_symbol):
                problem_list.append("多加换行")
        if CProblemType.比日文长 in find_type:
            if len(post_zh) > len(pre_jp) * 1.3:
                problem_list.append(
                    f"比日文长{round(len(post_zh)/max(len(pre_jp),0.1),1)}倍"
                )
        if CProblemType.字典使用 in find_type:
            if val := gpt_dict.check_dic_use(pre_zh, tran):
                problem_list.append(val)
        if arinashi_dict != {}:
            for key, value in arinashi_dict.items():
                if key not in pre_jp and value in post_zh:
                    problem_list.append(f"本无 {key} 译有 {value}")
                if key in pre_jp and value not in post_zh:
                    problem_list.append(f"本有 {key} 译无 {value}")

        if problem_list:
            tran.problem = ", ".join(problem_list)
        else:
            tran.problem = ""
