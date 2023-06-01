from GalTransl.CTranslate import CTransList
from json import dump


def save_transList_to_json_cn(trans_list: CTransList, save_path: str, name_dict={}):
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
        dump(result_list, f, ensure_ascii=False, indent=4)
