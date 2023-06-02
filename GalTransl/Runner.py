import time
from GalTransl.ConfigHelper import CProjectConfig
from GalTransl.Frontend.GPT import doGPT3Translate, doGPT4Translate, doNewBingTranslate
from GalTransl import LOGGER


async def run_galtransl(cfg: CProjectConfig, translator: str):
    start_time = time.time()
    if translator == "gpt35":
        await doGPT3Translate(cfg)
    elif translator == "gpt4":
        await doGPT4Translate(cfg)
    elif translator == "chatgpt-gpt35":
        await doGPT3Translate(cfg, type="unoffapi")
    elif translator == "chatgpt-gpt4":
        await doGPT4Translate(cfg, type="unoffapi")
    elif translator == "newbing":
        await doNewBingTranslate(cfg)
    elif translator == "caiyun":
        raise RuntimeError("Work in progress!")
    end_time = time.time()
    LOGGER.info(f"spend time:{str(end_time-start_time)}s")
