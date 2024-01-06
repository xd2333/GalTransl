import logging

logging.basicConfig(
    format="[%(asctime)s][%(levelname)s]%(message)s", level=logging.INFO
)

LOGGER = logging.getLogger(__name__)

PROGRAM_SPLASH = """
   ____       _ _____                    _ 
  / ___| __ _| |_   _| __ __ _ _ __  ___| |
 | |  _ / _` | | | || '__/ _` | '_ \/ __| |
 | |_| | (_| | | | || | | (_| | | | \__ \ |
  \____|\__,_|_| |_||_|  \__,_|_| |_|___/_|                                           
"""

GALTRANSL_VERSION = "3.3.0"
AUTHOR = "cx2333"
CONTRIBUTORS = "ryank231231, Isotr0py, Noriverwater, pipixia244, gulaodeng"

CONFIG_FILENAME = "config.yaml"
INPUT_FOLDERNAME = "json_jp"
OUTPUT_FOLDERNAME = "json_cn"
CACHE_FOLDERNAME = "transl_cache"
TRANSLATOR_SUPPORTED = {
    "gpt35-0613": "GPT3.5-Turbo API模式 0613模型",
    "gpt35-1106": "GPT3.5-Turbo API模式 1106模型",
    "gpt4": "GPT4 API模式",
    "gpt4-turbo": "GPT4-Turbo API模式",
    "newbing": "NewBing大小姐",
    "Sakura":"Sakura离线翻译 Sakura-13B-Galgame v0.9模型",
    "chatgpt-gpt35": "GPT3.5 模拟网页模式 -- 暂不可用",
    "chatgpt-gpt4": "GPT4 模拟网页模式 -- 暂不可用",
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
