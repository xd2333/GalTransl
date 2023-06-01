"""
CloseAI related classes
"""


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
