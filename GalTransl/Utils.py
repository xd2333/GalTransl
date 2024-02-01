"""
工具函数
"""
import os
import codecs
from typing import Tuple, List
from collections import Counter
from re import compile

PATTERN_CODE_BLOCK = compile(r"```([\w]*)\n([\s\S]*?)\n```")

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
        # 黑名单
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


def extract_code_blocks(content: str) -> Tuple[List[str], List[str]]:
    # 匹配带语言标签的代码块
    matches_with_lang = PATTERN_CODE_BLOCK.findall(content)

    # 提取所有匹配到的带语言标签的代码块
    lang_list = []
    code_list = []
    for match in matches_with_lang:
        lang_list.append(match[0])
        code_list.append(match[1])

    return lang_list, code_list


def get_file_name(file_path: str) -> str:
    """
    获取文件名，不包含扩展名
    """
    base_name = os.path.basename(file_path)
    file_name, _ = os.path.splitext(base_name)
    return file_name

def get_file_list(directory: str):
    file_list = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for file in filenames:
            file_list.append(os.path.join(dirpath, file))
    return file_list

def process_escape(text: str) -> str:
    return codecs.escape_decode(bytes(text, "utf-8"))[0].decode("utf-8")
