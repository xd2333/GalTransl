import time
from GalTransl.ConfigHelper import CProjectConfig, CProxyPool
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl.Frontend.GPT import doGPT3Translate, doGPT4Translate, doNewBingTranslate
from GalTransl import LOGGER


async def run_galtransl(cfg: CProjectConfig, translator: str):
    start_time = time.time()
    proxyPool = CProxyPool(cfg) if cfg.getKey("internals.enableProxy") else None
    OpenAITokenPool = COpenAITokenPool(cfg)
    if proxyPool:
        await proxyPool.checkAvailablity()
    if translator != "newbing":
        await OpenAITokenPool.checkTokenAvailablity(
            proxyPool.getProxy() if proxyPool else None
        )

    if translator == "gpt35":
        await doGPT3Translate(cfg, OpenAITokenPool, proxyPool)
    elif translator == "gpt4":
        await doGPT4Translate(cfg, OpenAITokenPool, proxyPool)
    elif translator == "chatgpt-gpt35":
        await doGPT3Translate(cfg, OpenAITokenPool, proxyPool, type="unoffapi")
    elif translator == "chatgpt-gpt4":
        await doGPT4Translate(cfg, OpenAITokenPool, proxyPool, type="unoffapi")
    elif translator == "newbing":
        await doNewBingTranslate(cfg, proxyPool)
    elif translator == "caiyun":
        raise RuntimeError("Work in progress!")
    end_time = time.time()
    LOGGER.info(f"spend time:{str(end_time-start_time)}s")
