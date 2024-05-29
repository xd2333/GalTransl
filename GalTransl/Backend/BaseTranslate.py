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
from GalTransl.Cache import get_transCache_from_json, save_transCache_to_json
from GalTransl.Dictionary import CGptDict
from GalTransl.Utils import extract_code_blocks, fix_quotes
from GalTransl.Backend.Prompts import (
    GPT4_CONF_PROMPT,
    GPT4_TRANS_PROMPT,
    GPT4_SYSTEM_PROMPT,
    GPT4_PROOFREAD_PROMPT,
    NAME_PROMPT4,
)
from GalTransl.Backend.Prompts import (
    GPT4Turbo_SYSTEM_PROMPT,
    GPT4Turbo_TRANS_PROMPT,
    GPT4Turbo_CONF_PROMPT,
    GPT4Turbo_PROOFREAD_PROMPT,
    H_WORDS_LIST,
)



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