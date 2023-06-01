from abc import abstractmethod, ABC
from GalTransl.CTranslate import CTransList

class ITranslator(ABC):
    @abstractmethod
    def __init__(self, config : dict) -> bool:
        """
        init translator and load config
        """
        pass
    @abstractmethod
    def init(self) -> bool:
        """
        call it before jobs
        """
        pass
    @abstractmethod
    def translate(self, content : CTransList) -> CTransList:
        """
        translate
        """
        pass
    @abstractmethod
    async def asyncTranslate(self, content : CTransList) -> CTransList:
        """
        translate with async requests
        """
        pass
    pass