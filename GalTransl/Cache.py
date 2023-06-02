"""
缓存机制
"""
from GalTransl.CSentense import CTransList
from GalTransl import LOGGER
from typing import List
from json import dump, load, JSONDecodeError
import os


def save_transCache_to_json(trans_list: CTransList, cache_file_path, proofread=False):
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
        dump(cache_json, f, ensure_ascii=False, indent=4)


def get_transCache_from_json(
    trans_list: CTransList, cache_file_path, retry_failed=False, proofread=False
):
    if not os.path.exists(cache_file_path):
        return [], trans_list

    trans_list_hit = []
    trans_list_unhit = []
    with open(cache_file_path, encoding="utf8") as f:
        try:
            cache_dictList = load(f)
        except JSONDecodeError:
            LOGGER.warn("读取缓存时出现错误，请重新启动程序。")
            f.close()  # 不然文件句柄还占用——删不了文件
            os.remove(cache_file_path)
            raise SystemExit

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
