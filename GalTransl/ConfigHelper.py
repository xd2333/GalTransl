from GalTransl import LOGGER
from typing import Optional
from random import randint
from yaml import safe_load
from os import path

# from jsonschema import validate
# from jsonschema.exceptions import ValidationError

SystemConfig: dict = {}


def initGPTToken(config: dict) -> Optional[list[dict]]:
    """
    处理 GPT Token 设置项
    """
    result: list[dict] = []
    degradeBackend: bool = False
    endpointURL: str = "https://api.openai.com"
    if "common" not in config:
        LOGGER.error("")
        return
    else:
        if "gpt.degradeBackend" not in config:
            pass  # use default
        else:
            degradeBackend = config["common"]["gpt.degradeBackend"]
    if "backendSpecific" not in config:
        LOGGER.error("")
        return
    else:
        if "GPT35" not in config["backendSpecific"]:
            LOGGER.error("")
            return
        else:
            if "defaultEndpoint" in config["backendSpecific"]["GPT35"]:
                endpointURL = config["backendSpecific"]["GPT35"]["defaultEndpoint"]
            if "token" in config["backendSpecific"]["GPT35"]:
                for tok in config["backendSpecific"]["GPT35"]["token"]:
                    if "token" not in tok:
                        LOGGER.error("token 解析错误")
                        return
                    result.append(
                        {
                            "token": tok["token"],
                            "endpoint": tok["endpoint"]
                            if "endpoint" in tok
                            else endpointURL,
                        }
                    )
                    pass
            else:
                LOGGER.error("必须在配置文件中指定GPT3.5密钥！")
                return
        if degradeBackend:
            if "token" in config["backendSpecific"]["GPT4"]:
                for tok in config["backendSpecific"]["GPT4"]["token"]:
                    if "token" not in tok:
                        LOGGER.error("token 解析错误")
                        return
                    result.append(
                        {
                            "token": tok["token"],
                            "endpoint": tok["endpoint"]
                            if "endpoint" in tok
                            else endpointURL,
                        }
                    )
                    pass
            else:
                LOGGER.error("")
                return

    return result


def randSelectInList(lst: list[dict]) -> dict:
    """
    随机选择一项（token或代理）
    """
    idx = randint(0, len(lst) - 1)
    return lst[idx]


def initProxyList(config: dict) -> Optional[list[dict]]:
    """
    处理代理设置项
    """
    result: list = []
    common = config.get("common")
    if not common:
        LOGGER.error("canont get 'common' section")
        return
    proxiesList = common.get("proxies")
    if not proxiesList:
        LOGGER.error("canont get 'proxies' section")
        return
    for i in proxiesList:
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
        result.append(str(path.abspath(projectDir) + "/" + entry))
    return result


def loadConfig(path: str) -> dict:
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
