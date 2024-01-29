import asyncio
import os
import time
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional
import datetime
import re
import json
import aiohttp
import requests



def send_message(
        payload
    ):
        url = "http://wxpusher.zjiecode.com/api/send/message"
        return _request("POST", url, json=payload)

def _request(method, url, **kwargs):
    with requests.request(method, url, **kwargs) as response:
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    weixinpush_token = "AT_A33lVU9Ksx4qUEZRHlWa54MmsU78VMmy"
    content = """<h3><a href="www.baidu.com" target="_blank">这是标题</a></h3>
                                <p><b>摘要：</b>这是描述</p>
                                <p><b>来源： </b>这是来源</p>
                                <p><b>发布时间：</b>这是发布时间</p>
    """
    payload = {
            "appToken": weixinpush_token,
            'content': content,
            'summary': "消息摘要3",
            'contentType': 2,
            'topicIds': [],
            'uids': ['UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz'],
            'verifyPay': False,
            'url': None
        }
    # payload = {
    #             "appToken": weixinpush_token,
    #             "content":"Wxpusher祝你中秋节快乐!",
    #             "summary":"消息摘要",
    #             "contentType": 3,
    #             "topicIds":[],
    #             "uids":[
    #                 "UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"
    #             ],
    #             "url":"https://baidu.com",
    #             "verifyPay":False
    #         }
    send_message(payload)
