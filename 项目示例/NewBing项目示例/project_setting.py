# -*- coding: utf-8 -*-
import os
from newbing_transl_api import *
from galtransl_core import *

# 修改这个为当前项目所在文件夹的位置，注意Windows下斜杠要双写，用\\
project_dir = "D:\\GalTransl-main\\项目示例\\NewBing项目示例"
# 通用字典文件夹位置，注意Windows下斜杠要双写，用\\
general_dic_dir = "D:\\GalTransl-main\\项目示例\\通用字典"
# 单次翻译句子数量，不建议太大
num_pre_request = 9
# 每次启动时重翻所有'Failed translation'，(True/False)（目前仅NewBing会翻译失败）
retry_fail = False
# 是否开启译后校润(True/False)
enable_proofread = False
num_pre_request_proofread = 7  # 不建议修改

# 代理设置，有代理则设置为类似proxy_url="http://127.0.0.1:10809"
proxy = ""

# ↓↓↓↓↓↓自动找问题配置↓↓↓↓↓↓
find_type = ["词频过高", "有无括号", "本无引号", "残留日文", "丢失换行", "多加换行"]
arinashi_dict = {}
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ==================================================================
# 载入newbing cookies文件
cookies_dir = os.path.join(project_dir, "newbing_cookies")
cookies_file_list = []
for file_name in os.listdir(cookies_dir):
    cookies_file_list.append(os.path.join(cookies_dir, file_name))

transl_api = NewBingTransl(cookies_file_list, proxy=proxy)

# GPT字典
gpt_dic_list=["GPT字典.txt"]
gpt_dic_list.append(os.path.join(project_dir, "项目GPT字典.txt"))


pre_dic_list=["00通用字典_译前.txt"]
pre_dic_list.append(os.path.join(project_dir, "项目字典_译前.txt"))#项目字典
post_dic_list=["00通用字典_译后.txt","00通用字典_符号_译后.txt"]
# post_dic_list.append("01H字典_矫正_译前.txt") #h矫正字典
post_dic_list.append(os.path.join(project_dir, "项目字典_译后.txt"))#项目字典

pre_dic = NormalDic(pre_dic_list, general_dic_dir)
post_dic = NormalDic(post_dic_list, general_dic_dir)
chatgpt_dic = GptDict(gpt_dic_list,general_dic_dir)

json_jp_dir = os.path.join(project_dir, "json_jp")
json_cn_dir = os.path.join(project_dir, "json_cn")
cache_dir = os.path.join(project_dir, "transl_cache")

if not os.path.exists(project_dir):
    print("请修改project_dir为项目所在文件夹的位置")
    exit(1)

for dir_path in [json_jp_dir, json_cn_dir, cache_dir]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
