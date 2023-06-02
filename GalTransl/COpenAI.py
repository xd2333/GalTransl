"""
CloseAI related classes
"""
from httpx import AsyncClient
from asyncio import gather

# from GalTransl.ConfigHelper import CProjectConfig


class COpenAITokenPool:
    """
    OpenAI 令牌池
    """

    def __init__(self) -> None:
        pass

    async def checkTokenAvailablity(self) -> None:
        """
        检测令牌有效性
        """
        pass


class COpenAIToken:
    """
    OpenAI 令牌
    """

    def __init__(self, token: str, domain: str, gpt3: bool, gpt4: bool) -> None:
        self.token: str = token
        self.domain: str = domain
        self.isGPT35Available: bool = gpt3
        self.isGPT4Available: bool = gpt4
        pass
