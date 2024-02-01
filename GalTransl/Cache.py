"""
缓存机制
"""
from GalTransl.CSentense import CTransList
from GalTransl import LOGGER
from typing import List
from json import dump, load, JSONDecodeError
import os


def save_transCache_to_json(trans_list: CTransList, cache_file_path, post_save=False):
    """
    此函数将翻译缓存保存到 JSON 文件中。

    Args:
        trans_list (CTransList): 要保存的翻译列表。
        cache_file_path (str): 要保存到的 JSON 文件的路径。
        post_save (bool, optional): 是否是翻译结束后的存储。默认为 False。
    """
    cache_json = []

    for tran in trans_list:
        if tran.pre_zh == tran.post_zh == "":
            continue

        cache_obj = {
            "index": tran.index,
            "name": tran.speaker,
            "pre_jp": tran.pre_jp,
            "post_jp": tran.post_jp,
            "pre_zh": tran.pre_zh,
        }

        cache_obj["proofread_zh"] = tran.proofread_zh

        if post_save and tran.problem != "":
            cache_obj["problem"] = tran.problem

        cache_obj["trans_by"] = tran.trans_by
        cache_obj["proofread_by"] = tran.proofread_by

        if tran.trans_conf != 0:
            cache_obj["trans_conf"] = tran.trans_conf
        if tran.doub_content != "":
            cache_obj["doub_content"] = tran.doub_content
        if tran.unknown_proper_noun != "":
            cache_obj["unknown_proper_noun"] = tran.unknown_proper_noun
        if post_save:
            cache_obj["post_zh_preview"] = tran.post_zh
        cache_json.append(cache_obj)

    with open(cache_file_path, mode="w", encoding="utf8") as f:
        dump(cache_json, f, ensure_ascii=False, indent=4)


def get_transCache_from_json(
    trans_list: CTransList,
    cache_file_path,
    retry_failed=False,
    proofread=False,
    retran_key="",
    load_post_jp=False,
    ignr_post_jp=False,
):
    """
    此函数从 JSON 文件中检索翻译缓存，并相应地更新翻译列表。

    Args:
        trans_list (CTransList): 要检索的翻译列表。
        cache_file_path (str): 包含翻译缓存的 JSON 文件的路径。
        retry_failed (bool, optional): 是否重试失败的翻译。默认为 False。
        proofread (bool, optional): 是否是校对模式。默认为 False。
        load_post_jp: 不检查post_jp是否被改变, 且直接使用cache的post_jp
        ignr_post_jp: 仅不检查post_jp是否被改变

    Returns:
        Tuple[List[CTrans], List[CTrans]]: 包含两个列表的元组：击中缓存的翻译列表和未击中缓存的翻译列表。
    """

    trans_list_hit = []
    trans_list_unhit = []

    if os.path.exists(cache_file_path):
        with open(cache_file_path, encoding="utf8") as f:
            try:
                cache_dictList = load(f)
                cache_dict = {cache["index"]: cache for cache in cache_dictList}
            except Exception as e:
                f.close()
                LOGGER.error(f"读取缓存{cache_file_path}时出现错误，请检查错误信息")
                raise e
    else:
        cache_dict = {}

    for tran in trans_list:
        # 忽略jp为空的句子
        if tran.pre_jp == "" or tran.post_jp == "":
            tran.pre_zh, tran.post_zh = "", ""
            trans_list_hit.append(tran)
            continue
        # 忽略在读取缓存前pre_zh就有值的句子
        if tran.pre_zh != "":
            tran.post_zh = tran.pre_zh
            trans_list_hit.append(tran)
            continue
        # index不在缓存
        if tran.index not in cache_dict:
            trans_list_unhit.append(tran)
            continue
        # post_jp被改变
        if load_post_jp == ignr_post_jp == False:
            if tran.post_jp != cache_dict[tran.index]["post_jp"]:
                trans_list_unhit.append(tran)
                continue
        # pre_zh为空
        if tran.post_jp != "":
            if (
                "pre_zh" not in cache_dict[tran.index]
                or cache_dict[tran.index]["pre_zh"] == ""
            ):
                trans_list_unhit.append(tran)
                continue
        # 重试失败的
        if retry_failed and "Failed translation" in cache_dict[tran.index]["pre_zh"]:
            if (
                cache_dict[tran.index]["proofread_zh"] == ""
                or "Fail" in cache_dict[tran.index]["proofread_by"]
            ):  # 且未校对
                trans_list_unhit.append(tran)
                continue

        # retran_key在pre_jp中
        if retran_key and retran_key in cache_dict[tran.index]["pre_jp"]:
            trans_list_unhit.append(tran)
            continue
        # retran_key在problem中
        if retran_key and "problem" in cache_dict[tran.index]:
            if retran_key in cache_dict[tran.index]["problem"]:
                trans_list_unhit.append(tran)
                continue

        # 击中缓存的,post_zh初始值赋pre_zh
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
        # if "problem" in cache_dict[tran.index]:
        #    tran.problem = cache_dict[tran.index]["problem"]

        if tran.proofread_zh != "":
            tran.post_zh = tran.proofread_zh
        else:
            tran.post_zh = tran.pre_zh

        # 校对模式下，未校对的
        if proofread and tran.proofread_zh == "":
            trans_list_unhit.append(tran)
            continue

        # 不检查post_jp是否被改变, 且直接使用cache的post_jp
        if load_post_jp:
            tran.post_jp = cache_dict[tran.index]["post_jp"]

        trans_list_hit.append(tran)

    return trans_list_hit, trans_list_unhit
