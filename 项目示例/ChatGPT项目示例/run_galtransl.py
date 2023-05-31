# -*- coding: utf-8 -*-
import os
import time
from project_setting import *
from galtransl_core import *

if not os.path.exists(project_dir):
    print("请修改project_dir为项目所在文件夹的位置")
    exit(1)
start_time = time.time()

for dir_path in [json_jp_dir, json_cn_dir, cache_dir]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        
for file_name in os.listdir(json_jp_dir):
    # 1、初始化trans_list
    trans_list = load_transList_from_json_jp(os.path.join(json_jp_dir, file_name))

    # 2、翻译前处理
    for i, tran in enumerate(trans_list):
        tran.analyse_dialogue()  # 解析是否为对话
        tran.post_jp = pre_dic.do_replace(tran.post_jp, tran)  # 译前字典替换

    # 3、读出未命中的Translate然后批量翻译
    cache_file_path = os.path.join(cache_dir, file_name)
    transl_api.batch_translate(
        file_name,
        cache_file_path,
        trans_list,
        num_pre_request,
        retry_failed=retry_fail,
        chatgpt_dict=chatgpt_dic,
    )

    # 4、翻译后处理
    for i, tran in enumerate(trans_list):
        tran.some_normal_fix()
        tran.recover_dialogue_symbol()  # 恢复对话框
        tran.post_zh = post_dic.do_replace(tran.post_zh, tran)  # 译后字典替换


    # 用于保存problems
    find_problems(
            trans_list,
            find_type=find_type,
            arinashi_dict=arinashi_dict
        )
    save_transCache_to_json(trans_list, cache_file_path)
    # 5、整理输出
    if os.path.exists(os.path.join(project_dir,"人名替换表.csv")):
        name_dict=load_name_table(os.path.join(project_dir,"人名替换表.csv"))
    else:
        name_dict={}
    save_transList_to_json_cn(trans_list, os.path.join(json_cn_dir, file_name),name_dict)


end_time = time.time()

print(f"spend time:{str(end_time-start_time)}s")
