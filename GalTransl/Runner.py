import time
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl.Frontend.GPT import (
    doGPT3Translate,
    doGPT4Translate,
    doNewBingTranslate,
    doSakuraTranslate,
    doRebuildTranslate
)
from GalTransl import LOGGER


async def run_galtransl(cfg: CProjectConfig, translator: str):
    start_time = time.time()
    proxyPool = CProxyPool(cfg) if cfg.getKey("internals.enableProxy") else None
    OpenAITokenPool = COpenAITokenPool(cfg)
    if proxyPool:
        await proxyPool.checkAvailablity()
    if "gpt35" in translator or "gpt4" in translator:
        await OpenAITokenPool.checkTokenAvailablity(
            proxyPool.getProxy() if proxyPool else None
        )

    if translator == "gpt35-0613":
        await doGPT3Translate(cfg, OpenAITokenPool, proxyPool, eng_type="gpt35-0613")
    elif translator == "gpt35-1106":
        await doGPT3Translate(cfg, OpenAITokenPool, proxyPool, eng_type="gpt35-1106")
    elif translator == "gpt4":
        await doGPT4Translate(cfg, OpenAITokenPool, proxyPool, eng_type="gpt4")
    elif translator == "gpt4-turbo":
        await doGPT4Translate(cfg, OpenAITokenPool, proxyPool, eng_type="gpt4-turbo")
    elif translator == "chatgpt-gpt35":
        await doGPT3Translate(cfg, OpenAITokenPool, proxyPool, eng_type="unoffapi")
    elif translator == "chatgpt-gpt4":
        await doGPT4Translate(cfg, OpenAITokenPool, proxyPool, eng_type="unoffapi")
    elif translator == "newbing":
        await doNewBingTranslate(cfg, proxyPool)
    elif translator == "Sakura":
        await doSakuraTranslate(cfg, proxyPool, eng_type="Sakura0.9")
    elif translator == "Rebuild":
        await doRebuildTranslate(cfg)

    end_time = time.time()
    LOGGER.info(f"spend time:{str(end_time-start_time)}s")
