from GalTransl import LOGGER
from GalTransl.CSentense import *
from os import path
from json import loads


def load_transList_from_json_jp(json_str_or_list: str):
    """
    从json文件路径、json字符串、json list中载入待翻译列表
    json格式为[{"name":xx/"names":[],"message/pre_jp":"xx"},...]
    """
    trans_list: CTransList = []

    if isinstance(json_str_or_list, str):
        if path.exists(json_str_or_list):
            with open(json_str_or_list, "r", encoding="utf-8") as f:
                json_str_or_list = f.read()
        json_list = loads(json_str_or_list)
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
        tmp_tran = CSentense(pre_jp, name, index)
        # 链接上下文
        if trans_list != []:
            tmp_tran.prev_tran = trans_list[-1]
            trans_list[-1].next_tran = tmp_tran
        trans_list.append(tmp_tran)

    return trans_list
