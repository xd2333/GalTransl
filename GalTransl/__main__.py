import argparse
import time
from os.path import join as joinpath
from os.path import exists as isPathExists
from os import makedirs as mkdir
from os import listdir
from GalTransl.ITranslater import ITranslator
from GalTransl.CChatGPTTranslate import CChatGPTTranslate
from GalTransl.ConfigHelper import loadConfig, initDictList, initGPTToken
from GalTransl.Loader import load_transList_from_json_jp
from GalTransl.Dictionary import CGptDict, CNormalDic
from GalTransl.Problem import find_problems
from GalTransl.Cache import save_transCache_to_json
from GalTransl.Name import load_name_table
from GalTransl.CSerialize import save_transList_to_json_cn
from GalTransl import LOGGER

# 暂时不扔配置文件里面
#
# ↓↓↓↓↓↓自动找问题配置↓↓↓↓↓↓
find_type = ["词频过高", "有无括号", "本无引号", "残留日文", "丢失换行", "多加换行"]
arinashi_dict = {}
# 单次翻译句子数量，不建议太大
num_pre_request = 9
# True/False,每次启动时重翻所有翻译失败的句子（目前仅NewBing会翻译失败）
retry_fail = True
# True/False,换行符改善模式，减少丢换行符情况，但可能导致循环重试
line_breaks_improvement_mode = False
# True/False,重启自动恢复上下文
restore_context_mode = True
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    parser = argparse.ArgumentParser("GalTransl")
    parser.add_argument("--project_dir", "-p", help="project folder", required=True)
    parser.add_argument("--config", "-c", help="filename of config file", required=True)
    parser.add_argument("--input", "-i", help="path of JSON text wait for translate")
    parser.add_argument("--output", "-o", help="path of outputed text")
    args = parser.parse_args()
    LOGGER.info("GalTransl v0.1.0 [2023-06-01]")
    cfg = loadConfig(joinpath(args.project_dir, args.config))

    # 加载字典
    pre_dic = CNormalDic(initDictList(cfg["common"]["dictionary"]["preDict"],args.project_dir))
    post_dic = CNormalDic(initDictList(cfg["common"]["dictionary"]["postDict"],args.project_dir))
    gpt_dic = CGptDict(initDictList(cfg["common"]["dictionary"]["gpt.dict"],args.project_dir))

    json_jp_dir = joinpath(args.project_dir, "json_jp")
    json_cn_dir = joinpath(args.project_dir, "json_cn")
    cache_dir = joinpath(args.project_dir, "transl_cache")
    gptapi = CChatGPTTranslate(cfg)
    gptapi.line_breaks_improvement_mode = line_breaks_improvement_mode
    gptapi.restore_context_mode = restore_context_mode

    # our journey begins
    start_time = time.time()
    for dir_path in [json_jp_dir, json_cn_dir, cache_dir]:
        if not isPathExists(dir_path):
            mkdir(dir_path)
    for file_name in listdir(json_jp_dir):
        # 1、初始化trans_list
        trans_list = load_transList_from_json_jp(joinpath(json_jp_dir, file_name))

        # 2、翻译前处理
        for i, tran in enumerate(trans_list):
            tran.analyse_dialogue()  # 解析是否为对话
            tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)  # 译前字典替换

        # 3、读出未命中的Translate然后批量翻译
        cache_file_path = joinpath(cache_dir, file_name)
        gptapi.batch_translate(
            file_name,
            cache_file_path,
            trans_list,
            num_pre_request,
            retry_failed=retry_fail,
            chatgpt_dict=gpt_dic,
        )

        # 4、翻译后处理
        for i, tran in enumerate(trans_list):
            tran.some_normal_fix()
            tran.recover_dialogue_symbol()  # 恢复对话框
            tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换

        # 用于保存problems
        find_problems(trans_list, find_type=find_type, arinashi_dict=arinashi_dict)
        save_transCache_to_json(trans_list, cache_file_path)
        # 5、整理输出
        if isPathExists(joinpath(args.project_dir, "人名替换表.csv")):
            name_dict = load_name_table(joinpath(args.project_dir, "人名替换表.csv"))
        else:
            name_dict = {}
        save_transList_to_json_cn(
            trans_list, joinpath(json_cn_dir, file_name), name_dict
        )

    end_time = time.time()

    print(f"spend time:{str(end_time-start_time)}s")

    pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(-1)