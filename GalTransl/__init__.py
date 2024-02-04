import logging
from time import localtime

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

PROGRAM_SPLASH1 = r"""
   ____       _ _____                    _ 
  / ___| __ _| |_   _| __ __ _ _ __  ___| |
 | |  _ / _` | | | || '__/ _` | '_ \/ __| |
 | |_| | (_| | | | || | | (_| | | | \__ \ |
  \____|\__,_|_| |_||_|  \__,_|_| |_|___/_|                 

------Translate your favorite Galgame------"""

PROGRAM_SPLASH2 = r"""
   ______      ________                      __
  / ____/___ _/ /_  __/________ _____  _____/ /
 / / __/ __ `/ / / / / ___/ __ `/ __ \/ ___/ / 
/ /_/ / /_/ / / / / / /  / /_/ / / / (__  ) /  
\____/\__,_/_/ /_/ /_/   \__,_/_/ /_/____/_/   
                                             
-------Translate your favorite Galgame-------                                        
"""
ALL_BANNERS = [PROGRAM_SPLASH1, PROGRAM_SPLASH2]
PROGRAM_SPLASH = ALL_BANNERS[localtime().tm_mday % 2]

GALTRANSL_VERSION = "4.0.2"
AUTHOR = "cx2333"
CONTRIBUTORS = "ryank231231, Isotr0py, Noriverwater, pipixia244, gulaodeng"

CONFIG_FILENAME = "config.yaml"
INPUT_FOLDERNAME = "gt_input"
OUTPUT_FOLDERNAME = "gt_output"
CACHE_FOLDERNAME = "transl_cache"
TRANSLATOR_SUPPORTED = {
    "gpt35-0613": "GPT3.5-Turbo API模式 -- 0613模型",
    "gpt35-1106": "GPT3.5-Turbo API模式 -- 1106模型",
    "gpt4-turbo": "GPT4-Turbo API模式 -- 0125-preview模型",
    "newbing": "NewBing 模拟网页模式",
    "sakura0.9": "Sakura-13B-Galgame翻译模型 -- v0.9模型",
    "rebuildr": "重建结果 用译前译后字典通过缓存刷写结果json -- 跳过翻译和写缓存",
    "rebuilda": "重建缓存和结果 用译前译后字典刷写缓存+结果json -- 跳过翻译",
    "showplugs": "显示全部插件列表",
}
LANG_SUPPORTED = {
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "fr": "French",
}
DEBUG_LEVEL = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}
