"""
CloseAI related classes
"""

from httpx import AsyncClient
import asyncio
from tqdm.asyncio import tqdm
from time import time
from GalTransl import LOGGER
from GalTransl.ConfigHelper import CProjectConfig, CProxy
from typing import Optional, Tuple
from random import choice
from asyncio import Queue

TRANSLATOR_ENGINE = {
    "gpt35": "gpt-3.5-turbo",
    "gpt35-0613": "gpt-3.5-turbo-0613",
    "gpt35-1106": "gpt-3.5-turbo-1106",
    "gpt35-0125": "gpt-3.5-turbo-0125",
    "gpt4": "gpt-4",
    "gpt4-turbo": "gpt-4-0125-preview",
}


class COpenAIToken:
    """
    OpenAI 令牌
    """

    def __init__(self, token: str, domain: str, gpt3: bool, gpt4: bool) -> None:
        self.token: str = token
        # it's domain, not endpoint address..
        self.domain: str = domain
        self.isGPT35Available: bool = gpt3
        self.isGPT4Available: bool = gpt4

    def maskToken(self) -> str:
        """
        返回脱敏后的 sk-
        """
        return self.token[:6] + "*" * 17


def initGPTToken(config: CProjectConfig, eng_type: str) -> Optional[list[COpenAIToken]]:
    """
    处理 GPT Token 设置项
    """
    result: list[dict] = []
    degradeBackend: bool = False

    if val := config.getKey("gpt.degradeBackend"):
        degradeBackend = val

    defaultEndpoint = "https://api.openai.com"
    gpt35_tokens = config.getBackendConfigSection("GPT35").get("tokens")
    if "gpt35" in eng_type and gpt35_tokens:
        for tokenEntry in gpt35_tokens:
            token = tokenEntry["token"]
            domain = (
                tokenEntry["endpoint"]
                if tokenEntry.get("endpoint")
                else defaultEndpoint
            )
            domain = domain[:-1] if domain.endswith("/") else domain
            result.append(COpenAIToken(token, domain, True, False))
            pass

        if not degradeBackend:
            return result

    if gpt4_tokens := config.getBackendConfigSection("GPT4").get("tokens"):
        for tokenEntry in gpt4_tokens:
            token = tokenEntry["token"]
            domain = (
                tokenEntry["endpoint"]
                if tokenEntry.get("endpoint")
                else defaultEndpoint
            )
            domain = domain[:-1] if domain.endswith("/") else domain
            result.append(
                COpenAIToken(token, domain, True if degradeBackend else False, True)
            )
            pass

    return result


class COpenAITokenPool:
    """
    OpenAI 令牌池
    """

    def __init__(self, config: CProjectConfig, eng_type: str) -> None:
        self.tokens: list[tuple[bool, COpenAIToken]] = []
        for token in initGPTToken(config, eng_type):
            self.tokens.append((False, token))
        if "gpt35" in eng_type:
            section = config.getBackendConfigSection("GPT35")
        elif "gpt4" in eng_type:
            section = config.getBackendConfigSection("GPT4")
        self.force_eng_name = section.get("rewriteModelName", "")

    async def _isTokenAvailable(
        self, token: COpenAIToken, proxy: CProxy = None, eng_type: str = ""
    ) -> Tuple[bool, bool, bool, COpenAIToken]:
        # returns isAvailable,isGPT3Available,isGPT4Available,token
        # todo: do not remove token directly, we can score the token
        try:
            st = time()
            async with AsyncClient(
                proxies={"https://": proxy.addr} if proxy else None
            ) as client:
                auth = {"Authorization": "Bearer " + token.token}
                model_name = TRANSLATOR_ENGINE.get(eng_type, "gpt-3.5-turbo")
                if self.force_eng_name:
                    model_name = self.force_eng_name
                # test if have balance
                chatResponse = await client.post(
                    token.domain + "/v1/chat/completions",
                    headers=auth,
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": "Echo OK"}],
                        "temperature": 0.7,
                    },
                    timeout=10,
                )
                if chatResponse.status_code != 200:
                    # token not available, may token has been revoked
                    return False, False, False, token
                else:
                    isGPT3Available = False
                    isGPT4Available = False

                    if "gpt-4" in model_name:
                        isGPT4Available = True
                    elif "gpt-3.5" in model_name:
                        isGPT3Available = True
                    else:
                        isGPT4Available, isGPT3Available = True, True

                    return True, isGPT3Available, isGPT4Available, token
        except:
            LOGGER.debug(
                "we got exception in testing OpenAI token %s", token.maskToken()
            )
            return False, False, False, token
        finally:
            et = time()
            LOGGER.debug("tested OpenAI token %s in %s", token.maskToken(), et - st)
            pass

    async def _check_token_availability_with_retry(
        self,
        token: COpenAIToken,
        proxy: CProxy = None,
        eng_type: str = "",
        max_retries: int = 3,
    ) -> Tuple[bool, bool, bool, COpenAIToken]:
        for retry_count in range(max_retries):
            is_available, is_gpt3_available, is_gpt4_available, token = (
                await self._isTokenAvailable(token, proxy, eng_type)
            )
            if is_available:
                return is_available, is_gpt3_available, is_gpt4_available, token
            else:
                # wait for some time before retrying, you can add some delay here
                await asyncio.sleep(1)

        # If all retries fail, return the result from the last attempt
        return is_available, is_gpt3_available, is_gpt4_available, token

    async def checkTokenAvailablity(
        self, proxy: CProxy = None, eng_type: str = ""
    ) -> None:
        """
        检测令牌有效性
        """
        model_name = TRANSLATOR_ENGINE.get(eng_type, "gpt-3.5-turbo")
        if self.force_eng_name:
            model_name = self.force_eng_name
        if model_name == "gpt-3.5-turbo-0125":
            raise RuntimeError("gpt-3.5-turbo-0125质量太差，请更换其他模型！")
        LOGGER.info(f"测试key是否能调用{model_name}模型...")
        fs = []
        for _, token in self.tokens:
            fs.append(
                self._check_token_availability_with_retry(
                    token, proxy if proxy else None, eng_type
                )
            )
        result: list[tuple[bool, bool, bool, COpenAIToken]] = await tqdm.gather(
            *fs, ncols=80
        )

        # replace list with new one
        newList: list[tuple[bool, COpenAIToken]] = []
        for isAvailable, isGPT3Available, isGPT4Available, token in result:
            if isAvailable != True:
                LOGGER.warning(
                    "%s is not available for %s, will be removed",
                    token.maskToken(),
                    model_name,
                )
            else:
                newList.append((True, token))

        self.tokens = newList

    def reportTokenProblem(self, token: COpenAIToken) -> None:
        """
        报告令牌无效
        """
        for id, tokenPair in enumerate(self.tokens):
            if tokenPair[1] == token:
                self.tokens.pop(id)
            pass
        pass

    def getToken(self, needGPT3: bool, needGPT4: bool) -> COpenAIToken:
        """
        获取一个有效的 token
        """
        rounds: int = 0
        while True:
            if rounds > 20:
                raise RuntimeError(
                    "COpenAITokenPool::getToken: 可用的API key耗尽！"
                )
            try:
                available, token = choice(self.tokens)
                if not available:
                    continue
                if needGPT3 and token.isGPT35Available:
                    return token
                if needGPT4 and token.isGPT4Available:
                    return token
                rounds += 1
            except IndexError:
                raise RuntimeError("没有可用的 API key！")


async def init_sakura_endpoint_queue(
    projectConfig: CProjectConfig
) -> Optional[Queue]:
    """
    初始化端点队列，用于Sakura或GalTransl引擎。

    参数:
    projectConfig: 项目配置对象
    workersPerProject: 每个项目的工作线程数
    eng_type: 引擎类型

    返回:
    初始化的端点队列，如果不需要则返回None
    """

    workersPerProject = projectConfig.getKey("workersPerProject") or 1
    sakura_endpoint_queue = asyncio.Queue()
    backendSpecific = projectConfig.projectConfig["backendSpecific"]
    section_name = "SakuraLLM" if "SakuraLLM" in backendSpecific else "Sakura"
    if "endpoints" in projectConfig.getBackendConfigSection(section_name):
        endpoints = projectConfig.getBackendConfigSection(section_name)["endpoints"]
    else:
        endpoints = [
            projectConfig.getBackendConfigSection(section_name)["endpoint"]
        ]
    repeated = (workersPerProject + len(endpoints) - 1) // len(endpoints)
    for _ in range(repeated):
        for endpoint in endpoints:
            await sakura_endpoint_queue.put(endpoint)
    LOGGER.info(f"当前使用 {workersPerProject} 个Sakura worker引擎")
    return sakura_endpoint_queue