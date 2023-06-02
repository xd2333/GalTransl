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

CONFIG_FILENAME = "config.yaml"

INPUT_FOLDERNAME = "json_jp"
OUTPUT_FOLDERNAME = "json_cn"
CACHE_FOLDERNAME = "transl_cache"
TRANSLATOR_SUPPORTED = [
    "gpt35",
    "chatgpt-gpt35",
    "gpt4",
    "chatgpt-gpt4",
    "newbing",
    "caiyun",
]
