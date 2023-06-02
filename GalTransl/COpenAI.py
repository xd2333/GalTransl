"""
CloseAI related classes
"""
import httpx


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


class COpenAITokenPool:
    """
    OpenAI 令牌池
    """

    def __init__(self) -> None:
        pass

    async def updateFromFreeOpenAI(self) -> None:
        """
        https://freeopenai.xyz/
        """
        pass

    async def removeInvaildToken(self) -> None:
        """
        检测令牌有效性
        """
        pass
