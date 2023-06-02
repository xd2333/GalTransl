"""
读取 / 处理配置
"""
from GalTransl import (
    LOGGER,
    CONFIG_FILENAME,
    INPUT_FOLDERNAME,
    OUTPUT_FOLDERNAME,
    CACHE_FOLDERNAME,
)
from GalTransl.COpenAI import COpenAIToken
from GalTransl.Problem import CTranslateProblem
from typing import Optional
from random import randint
from yaml import safe_load
from os import path, sep


class CProjectConfig:
    def __init__(self, projectPath: str) -> None:
        self.projectConfig = loadConfigFile(path.join(projectPath, CONFIG_FILENAME))
        self.projectDir: str = projectPath
        self.inputPath: str = str(
            path.abspath(path.join(projectPath, INPUT_FOLDERNAME))
        )
        self.outputPath: str = str(
            path.abspath(path.join(projectPath, OUTPUT_FOLDERNAME))
        )
        self.cachePath: str = str(
            path.abspath(path.join(projectPath, CACHE_FOLDERNAME))
        )
        self.keyValues = dict()
        for k,v in self.projectConfig["common"].items():
            self.keyValues[k] = v
        pass
        LOGGER.info(
            "inputPath: %s, outputPath: %s, cachePath: %s,keyValues: %s",
            self.inputPath,
            self.outputPath,
            self.cachePath,
            self.keyValues,
        )

    def getProjectConfig(self) -> dict:
        """
        获取解析的 YAML 配置文件
        """
        return self.projectConfig

    def getProjectDir(self) -> str:
        return self.projectDir

    def getInputPath(self) -> str:
        return self.inputPath

    def getOutputPath(self) -> str:
        return self.outputPath

    def getCachePath(self) -> str:
        return self.cachePath

    def getCommonConfigSection(self) -> dict:
        return self.projectConfig["common"]

    def getProxyConfigSection(self) -> dict:
        return self.projectConfig["proxies"]

    def getBackendConfigSection(self, backendName: str) -> dict:
        """
        backendName: GPT35 / GPT4 / ChatGPT / bingGPT4
        """
        return self.projectConfig["backendSpecific"][backendName]

    def getDictCfgSection(self) -> dict:
        return self.projectConfig["dictionary"]

    def getKey(self, key: str) -> str | bool | int | None:
        return self.keyValues.get(key)

    def getProblemAnalyzeConfig(self, backendName: str) -> list[CTranslateProblem]:
        result: list[CTranslateProblem] = []
        for i in self.projectConfig["problemAnalyze"][backendName]:
            result.append(CTranslateProblem[i])

        return result


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
                if tokenEntry["endpoint"]
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
                if tokenEntry["endpoint"]
                else config.getBackendConfigSection("GPT35")["defaultEndpoint"],
                True if degradeBackend else False,
                True,
            )
        )
        pass

    return result


def randSelectInList(lst: list[dict]) -> dict:
    """
    随机选择一项（token或代理）
    """
    idx = randint(0, len(lst) - 1)
    return lst[idx]


def initProxyList(config: CProjectConfig) -> Optional[list[dict]]:
    """
    处理代理设置项
    """
    result: list = []
    for i in config.getProxyConfigSection():
        result.append(
            {
                "addr": i["address"],
                "username": i.get("username"),
                "password": i.get("password"),
            }
        )

    return result


def initDictList(config: dict, projectDir: str) -> Optional[list[str]]:
    """
    处理字典设置项
    """
    result: list[str] = []
    for entry in config:
        result.append(str(path.abspath(projectDir) + sep + entry))
    return result


def loadConfigFile(path: str) -> dict:
    """
    加载项目配置文件（YAML）
    """
    with open(path, "rb") as cfgfile:
        cfg: dict = {}
        try:
            cfg = safe_load(cfgfile.read())
        except Exception as err:
            LOGGER.error(f"error parsing config file: {err}")
            return False
        """
        try:
            validate(cfg)
        except ValidationError as err:
            LOGGER.error(f"config file is invaild: {err}")
            return False
        """
        return cfg
