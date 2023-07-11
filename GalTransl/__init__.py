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

GALTRANSL_VERSION = "2.4.0"
AUTHOR = "cx2333"
CONTRIBUTORS = "ryank231231, Isotr0py"

CONFIG_FILENAME = "config.yaml"
INPUT_FOLDERNAME = "json_jp"
OUTPUT_FOLDERNAME = "json_cn"
CACHE_FOLDERNAME = "transl_cache"
TRANSLATOR_SUPPORTED = {
    "gpt35": "GPT3.5 官方API",
    "chatgpt-gpt35": "GPT3.5 模拟网页操作模式",
    "gpt4": "GPT4 官方API",
    "chatgpt-gpt4": "GPT4 模拟网页操作模式",
    "newbing": "NewBing大小姐",
    "caiyun": "彩云 -- 暂不可用",
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
