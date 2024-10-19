import json, time, asyncio, os, traceback
from opencc import OpenCC
from typing import Optional
from GalTransl.COpenAI import COpenAITokenPool
from GalTransl.ConfigHelper import CProxyPool
from GalTransl import LOGGER, LANG_SUPPORTED
from sys import exit
from GalTransl.ConfigHelper import (
    CProjectConfig,
)
from random import choice
from GalTransl.CSentense import CSentense, CTransList
from GalTransl.Cache import get_transCache_from_json_new, save_transCache_to_json
from GalTransl.Dictionary import CGptDict
from GalTransl.Utils import extract_code_blocks, fix_quotes



class BaseTranslate:
    def __init__(
        self,
        config: CProjectConfig,
        eng_type: str,
        proxy_pool: Optional[CProxyPool],
        token_pool: COpenAITokenPool,
    ):
        pass

    def init_chatbot(self, eng_type, config):
        pass

    def clean_up(self):
        pass

    def translate(self, trans_list: CTransList, gptdict=""):
        pass
