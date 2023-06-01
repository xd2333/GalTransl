import os
from gpt4_transl_api import *
from galtransl_core import *

# 修改为这个项目所在文件夹的位置，注意Windows下斜杠要双写，用\\
project_dir = "D:\\GalTransl-main\\项目示例\\GPT4项目示例"
# 修改这个为通用字典目录位置
general_dic_dir = "D:\\GalTransl-main\\项目示例\\通用字典"

# API类型，offapi为官方API,unoffapi为模拟网页操作
api_type = "offapi"

# ↓↓↓↓↓↓官方api接口调用设置↓↓↓↓↓↓
# 修改为你的api_key
openai_api_key = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# 调用openai api的URL，默认为官方地址，如果你有转发网站，把api.openai.com部分改为你的域名
openai_api_url = "https://api.openai.com"
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# ↓↓↓↓↓↓模拟网页操作接口调用设置↓↓↓↓↓↓
# 访问https://chat.openai.com/api/auth/session，提取access_token的值，填入下面
access_token = ""
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# 代理设置，有代理则设置为类似proxy_url="http://127.0.0.1:10809"
proxy_url = ""

# 单次翻译句子数量，不建议太大
num_pre_request = 10
# True/False,每次启动时重翻所有翻译失败的句子（目前仅NewBing会翻译失败）
retry_fail = True
# True/False,重启自动恢复上下文
auto_restore_context_mode = True
# True/False,记录置信度、存疑句、未知专有名词，使用官方API时关闭可以节省Token
record_confidence = False
# 是否开启译后校润(True/False)
enable_proofread = False
num_pre_request_proofread = 7  # 不建议修改

# ↓↓↓↓↓↓自动找问题配置↓↓↓↓↓↓
find_type = ["词频过高", "有无括号", "本无引号", "残留日文", "丢失换行", "多加换行"]
arinashi_dict = {}
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# GPT字典
gpt_dic_list = ["GPT字典.txt"]
gpt_dic_list.append(os.path.join(project_dir, "项目GPT字典.txt"))

# 普通字典
pre_dic_list = ["00通用字典_译前.txt"]
pre_dic_list.append("01H字典_矫正_译前.txt")  # h矫正字典
pre_dic_list.append(os.path.join(project_dir, "项目字典_译前.txt"))  # 项目字典

post_dic_list = ["00通用字典_译后.txt", "00通用字典_符号_译后.txt"]
post_dic_list.append(os.path.join(project_dir, "项目字典_译后.txt"))  # 项目字典

pre_dic = NormalDic(pre_dic_list, general_dic_dir)
post_dic = NormalDic(post_dic_list, general_dic_dir)
chatgpt_dic = GptDict(gpt_dic_list, general_dic_dir)

json_jp_dir = os.path.join(project_dir, "json_jp")
json_cn_dir = os.path.join(project_dir, "json_cn")
cache_dir = os.path.join(project_dir, "transl_cache")

if not openai_api_url.endswith("/v1/chat/completions"):
    openai_api_url = openai_api_url + "/v1/chat/completions"

os.environ["API_URL"] = openai_api_url
transl_api = ChatgptTrans(
    api_type, apikey=openai_api_key,access_token=access_token, proxy=proxy_url
)
transl_api.record_confidence = record_confidence
transl_api.restore_context_mode = auto_restore_context_mode
