import hashlib
import json
import random
import time
from asyncio import sleep

import requests

from GalTransl import LOGGER
from GalTransl.CSentense import CTransList


class CaiyunTransl:
    def __init__(self, token) -> None:
        self.page_id, self.request_id, self.caiyun_rand_url = self.init_caiyun_request()
        self.token = token

    def init_caiyun_request(self):
        """程序启动前调用一次，随机化彩云的请求

        Returns:
            _type_: _description_
        """
        page_id = ""
        request_id = ""
        url = ""
        url_list = [
            ["http://www.getchu.com/", 206382],
            ["http://www.getchu.com/pc/", 655498],
            ["http://www.getchu.com/books/", 2354631],
        ]

        random_str = str(time.time())
        random_md5 = hashlib.md5(random_str.encode("utf-8")).hexdigest()
        request_id = random_md5[:24]

        rand_int = random.randint(0, len(url_list) - 1)
        page_id = url_list[rand_int][1]
        url = url_list[rand_int][0]

        return page_id, request_id, url

    async def caiyun_translate(self, trans_list: CTransList):
        """
        调用彩云API翻译
        """
        burp0_url = "https://api.interpreter.caiyunai.com:443/v1/translator"
        burp0_headers = {
            "X-Authorization": "token " + self.token,
            "content-type": "application/json",
        }
        jp_list = []
        for trans in trans_list:
            # print(trans.post_jp)
            jp_list.append(trans.post_jp)

        burp0_json = {
            "request_id": self.request_id,
            "source": jp_list,
            "trans_type": "ja2zh",
        }
        while True:  # 一直循环，直到得到数据
            try:
                resp = requests.post(
                    burp0_url, headers=burp0_headers, json=burp0_json, timeout=10
                )
                if resp.status_code == 200 and "target" in resp.text:
                    break
                else:
                    print("request error code:" + str(resp.status_code))
                    await sleep(3)
            except:
                print("Connect Error, Please wait 3 seconds")
                await sleep(3)

        result_json = json.loads(resp.text)

        for i, result in enumerate(result_json["target"]):
            tran_result = result["target"].replace(" ", "")
            trans_list[i].pre_zh = tran_result
            trans_list[i].post_zh = tran_result

        return trans_list

    async def batch_translate(
        self, filename, trans_list: CTransList, num_pre_request: int
    ) -> CTransList:
        """调用彩云批量翻译这个transList

        Args:
            filename (str): txt文件名
            trans_list (CTransList): transList
            num_pre_request (int): 每次提交多少个句子，推荐30

        Returns:
            CTransList: 翻译好的transList，不过没啥用
        """

        i = 0
        trans_result_list = []
        len_trans_list = len(trans_list)
        while i < len_trans_list:
            await sleep(1)
            trans_result = (
                self.caiyun_translate(trans_list[i : i + num_pre_request])
                if (i + num_pre_request < len_trans_list)
                else self.caiyun_translate(trans_list[i:])
            )
            i += num_pre_request
            for trans in trans_result:
                print(trans.pre_zh)
            trans_result_list += trans_result
            print(f"{filename}：{str(len(trans_result_list))}/{str(len_trans_list)}")

        return trans_result_list
