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

# from GalTransl.COpenAI import COpenAIToken
from GalTransl.Problem import CTranslateProblem
from asyncio import gather
from httpx import AsyncClient, TimeoutException
from time import time
from typing import Optional
from random import choice
from yaml import safe_load
from os import path, sep


class CProxy:
    def __init__(
        self,
        address: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.addr = address
        self.username = username
        self.pw = password
        pass


class CProjectConfig:
    def __init__(self, projectPath: str, config_name=CONFIG_FILENAME) -> None:
        self.projectConfig = loadConfigFile(path.join(projectPath, config_name))
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
        for k, v in self.projectConfig["common"].items():
            self.keyValues[k] = v
        self.keyValues["internals.enableProxy"] = self.projectConfig["proxy"][
            "enableProxy"
        ]
        LOGGER.debug(
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
        return self.projectConfig["proxy"]["proxies"]

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

    def getProblemAnalyzeArinashiDict(self) -> dict:
        return self.projectConfig["problemAnalyze"]["arinashiDict"]


class CProxyPool:
    def __init__(self, config: CProjectConfig) -> None:
        self.proxies: list[tuple[bool, CProxy]] = []
        for i in config.getProxyConfigSection():
            self.proxies.append(
                (False, CProxy(i["address"], i.get("username", i.get("password"))))
            )

    async def _availablityChecker(
        self, proxy: CProxy, test_address="http://www.gstatic.com/generate_204"
    ) -> tuple[bool, CProxy]:
        try:
            st = time()
            LOGGER.debug("start testing proxy %s", proxy.addr)
            async with AsyncClient(proxies={"http://": proxy.addr}) as client:
                response = await client.get(test_address)
                if response.status_code != 204:
                    LOGGER.debug("tested proxy %s failed (%s)", proxy.addr, response)
                    return False, proxy
                else:
                    return True, proxy
        except TimeoutException:
            LOGGER.debug("we got exception in testing proxy %s", proxy.addr)
            return False, proxy
        except:
            LOGGER.debug("we got exception in testing proxy %s", proxy.addr)
            raise
            return False, proxy
        finally:
            et = time()
            LOGGER.debug("tested proxy %s in %s", proxy.addr, et - st)
            pass

    async def checkAvailablity(self) -> None:
        fs = []
        for _, proxy in self.proxies:
            fs.append(self._availablityChecker(proxy))
        result: list[tuple[bool, CProxy]] = await gather(*fs)
        newList: list[tuple[bool, CProxy]] = []
        for proxyStatus, proxy in result:
            if proxyStatus != True:
                LOGGER.info("removed proxy %s, because it's not available", proxy.addr)
            else:
                newList.append((True, proxy))
        self.proxies = newList

    def getProxy(self) -> CProxy:
        rounds: int = 0
        while True:
            if rounds > 10:
                raise RuntimeError("CProxyPool::getProxy: 迭代次数过多！")
            available, proxy = choice(self.proxies)
            if not available:
                rounds += 1
                continue
            else:
                return proxy


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


def initDictList(config: dict, dictDir: str, projectDir: str) -> Optional[list[str]]:
    """
    处理字典设置项
    """
    result: list[str] = []
    for entry in config:
        if entry.startswith("(project_dir)"):
            entry = entry.replace("(project_dir)", "")
            result.append(str(path.abspath(projectDir) + sep + entry))
        else:
            result.append(str(path.abspath(dictDir) + sep + entry))
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
