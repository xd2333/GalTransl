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

GALTRANSL_VERSION = "4.1.1"
AUTHOR = "cx2333"
CONTRIBUTORS = "ryank231231, Isotr0py, Noriverwater, pipixia244, gulaodeng, PiDanShouRouZhouXD"

CONFIG_FILENAME = "config.yaml"
INPUT_FOLDERNAME = "gt_input"
OUTPUT_FOLDERNAME = "gt_output"
CACHE_FOLDERNAME = "transl_cache"
TRANSLATOR_SUPPORTED = {
    "gpt35-0613": "GPT3.5-Turbo-0613 API模式",
    "gpt35-1106": "GPT3.5-Turbo-1106 API模式",
    "gpt4-turbo": "GPT4-Turbo-1125 API模式(兼容claude3-opus第三方中转API)",
    "newbing": "NewBing 模拟网页模式",
    "sakura-010": "SakuraLLM翻译模型 -- 适用0.10模型",
    "sakura-009": "SakuraLLM翻译模型 -- 适用0.09模型",
    "rebuildr": "重建结果 用译前译后字典通过缓存刷写结果json -- 跳过翻译和写缓存",
    "rebuilda": "重建缓存和结果 用译前译后字典刷写缓存+结果json -- 跳过翻译",
    "showplugs": "显示全部插件列表",
}
LANG_SUPPORTED = {
    "zh-cn": "Simplified_Chinese",
    "zh-tw": "Traditional_Chinese",
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
