"""
CloseAI related classes
"""
from httpx import AsyncClient
from asyncio import gather
from time import time
from GalTransl import LOGGER
from GalTransl.ConfigHelper import CProjectConfig, CProxy
from typing import Optional, Tuple
from random import choice


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
        return self.token[:5] + "*" * 18


def initGPTToken(config: CProjectConfig) -> Optional[list[COpenAIToken]]:
    """
    处理 GPT Token 设置项
    """
    result: list[dict] = []
    degradeBackend: bool = False
    endpointDomain: str = "https://api.openai.com"

    if val := config.getKey("gpt.degradeBackend"):
        degradeBackend = val

    for tokenEntry in config.getBackendConfigSection("GPT35").get("tokens"):
        result.append(
            COpenAIToken(
                tokenEntry["token"],
                tokenEntry["endpoint"]
                if tokenEntry.get("endpoint")
                else config.getBackendConfigSection("GPT35")["defaultEndpoint"],
                True,
                False,
            )
        )
        pass
    for tokenEntry in config.getBackendConfigSection("GPT4").get("tokens"):
        result.append(
            COpenAIToken(
                tokenEntry["token"],
                tokenEntry["endpoint"]
                if tokenEntry.get("endpoint")
                else config.getBackendConfigSection("GPT35")["defaultEndpoint"],
                True if degradeBackend else False,
                True,
            )
        )
        pass

    return result


class COpenAITokenPool:
    """
    OpenAI 令牌池
    """

    def __init__(self, config: CProjectConfig) -> None:
        self.tokens: list[tuple[bool, COpenAIToken]] = []
        for token in initGPTToken(config):
            self.tokens.append((False, token))

    async def _isTokenAvailable(
        self, token: COpenAIToken, proxy: CProxy = None
    ) -> Tuple[bool, bool, bool, COpenAIToken]:
        # returns isAvailable,isGPT3Available,isGPT4Available,token
        # todo: do not remove token directly, we can score the token
        try:
            st = time()
            async with AsyncClient(
                proxies={"https://": proxy.addr} if proxy else None
            ) as client:
                auth = {"Authorization": "Bearer " + token.token}
                modelResponse = await client.get(
                    token.domain + "/v1/models", headers=auth
                )
                if modelResponse.status_code != 200:
                    # token not available, may token has been revoked
                    return False, False, False, token
                else:
                    # test if have balance
                    chatResponse = await client.post(
                        token.domain + "/v1/chat/completions",
                        headers=auth,
                        json={
                            "model": "gpt-3.5-turbo",
                            "messages": [{"role": "user", "content": "Echo OK"}],
                            "temperature": 0.7,
                        },
                    )
                    if chatResponse.status_code != 200:
                        # token not available, may token has been revoked
                        return False, False, False, token
                    else:
                        isGPT3Available = False
                        isGPT4Available = False
                        for model in modelResponse.json()["data"]:
                            if model["id"] == "gpt-4":
                                isGPT4Available = True
                            elif model["id"] == "gpt-3.5-turbo":
                                isGPT3Available = True
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

    async def checkTokenAvailablity(self, proxy: CProxy = None) -> None:
        """
        检测令牌有效性
        """
        fs = []
        for _, token in self.tokens:
            fs.append(self._isTokenAvailable(token, proxy if proxy else None))
        result: list[tuple[bool, bool, bool, COpenAIToken]] = await gather(*fs)

        # replace list with new one
        newList: list[tuple[bool, COpenAIToken]] = []
        for isAvailable, isGPT3Available, isGPT4Available, token in result:
            if isAvailable != True:
                LOGGER.info(
                    "removed OpenAI token %s, because it's not available",
                    token.maskToken(),
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
                self.tokens[id][0] = False
            pass
        pass

    def getToken(self, needGPT3: bool, needGPT4: bool) -> COpenAIToken:
        """
        获取一个有效的 token
        """
        rounds: int = 0
        while True:
            if rounds > 20:
                raise RuntimeError("COpenAITokenPool::getToken: 迭代次数过多！")
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
                raise RuntimeError("没有可用的 OpenAI token！")
