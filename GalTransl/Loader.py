from GalTransl import LOGGER
from GalTransl.CSentense import *
from os import path
from json import loads


def load_transList(json_path_or_list: str | list) -> tuple[CTransList, list]:
    """
    从json文件路径、json字符串、json list中载入待翻译列表
    json格式为[{"name":xx/"names":[],"message/pre_jp":"xx"},...]
    """
    trans_list: CTransList = []

    if isinstance(json_path_or_list, str):
        assert path.exists(json_path_or_list), f"{json_path_or_list}不存在"
        with open(json_path_or_list, "r", encoding="utf-8") as f:
            try:
                json_list = loads(f.read())
            except Exception as e:
                raise e
    elif isinstance(json_path_or_list, list):
        json_list = json_path_or_list

    for i, item in enumerate(json_list):
        assert "message" in item, f"json格式不正确，第{str(i+1)}个item缺少message字段：{item}"

        name = (
            item["name"] if "name" in item else item["names"] if "names" in item else ""
        )
        pre_jp = item["message"]
        index = item["index"] if "index" in item else i + 1
        tmp_tran = CSentense(pre_jp, name, index)
        # 链接上下文
        if trans_list != []:
            tmp_tran.prev_tran = trans_list[-1]
            trans_list[-1].next_tran = tmp_tran
        trans_list.append(tmp_tran)

    return trans_list, json_list
