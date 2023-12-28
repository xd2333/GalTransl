from GalTransl.CSentense import CTransList
from json import dump


def save_transList_to_json_cn(trans_list: CTransList, save_path: str, name_dict={}):
    result_list = []
    for tran in trans_list:
        if tran.speaker != "":
            if type(tran.speaker) == list:
                result_name = []
                for name in tran.speaker:
                    result_name.append(name_dict[name] if name in name_dict else name)
                result_list.append({"names": result_name, "message": tran.post_zh})
            else:
                result_name = (
                    name_dict[tran.speaker]
                    if tran.speaker in name_dict
                    else tran.speaker
                )
                result_list.append({"name": result_name, "message": tran.post_zh})
        else:
            result_list.append({"message": tran.post_zh})
    with open(save_path, "w", encoding="utf8") as f:
        dump(result_list, f, ensure_ascii=False, indent=4)
