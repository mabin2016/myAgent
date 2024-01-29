import asyncio
import os
import time
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional
import datetime
import re
import json
import ast

import aiohttp
from aiocron import crontab
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from pytz import BaseTzInfo

from metagpt.actions.action import Action
from metagpt.config import CONFIG
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.subscription import SubscriptionRunner
from metagpt.environment import Environment
from langchain_community.chat_message_histories import SQLChatMessageHistory


Environment

memory = SQLChatMessageHistory(session_id="user_session_id", connection_string="sqlite:///sqlite.db")

weixinpush_token = "AT_A33lVU9Ksx4qUEZRHlWa54MmsU78VMmy"
tophub_today_token = "1b29fbc5a669bdcaa50201bedbcfa614"
weixinpush_base_url = "http://wxpusher.zjiecode.com"



class CrawlOSSRanking(Action):
   
   query: str = ""

   async def run(self, query: str = ""):
       res = await self.detect_entity(query)
       return await self.crawl_api(res["words"][0], res["num"])
       
   async def crawl_api(self, word: str = "", num: int = 10):
        memory.add_user_message(word)
        url = f"https://api.tophubdata.com/search?q={word}"
        async with aiohttp.ClientSession() as client:
            headers = {"Authorization": tophub_today_token}
            async with client.get(url, headers=headers) as response:
               response.raise_for_status()
               resp = await response.json()
        data = resp["data"]["items"][:num]
        for i, item in enumerate(data):
            data[i]["time"] = datetime.datetime.utcfromtimestamp(item['time']).strftime('%Y-%m-%d %H:%M:%S')
        return data
   
   async def detect_entity(self, query):
        json_example = '{"words": ["实体1", "实体2"], "num": 数字, "time": [crontab类型时间点1, crontab时间点2]}'
        json_text1 = '{"words": ["GPT"], "num", "time": ["30 18 * * *"]}'
        json_text2 = '{"words": ["巴以冲突", "朝鲜半岛"], "num", "time": ["* */1 * * *", "30 19 * * *"]}'
        prompt = """
    你是一个命名实体识别模型，用户输入自然语言，你从中提取出命名实体并将结果以json的形式返回，在返回结果时，我会保持准确性和简洁性，同时遵循用户指定的json格式：```json {json_example}```，
    如果用户没有指定num和time则num=10，time="* 9 * * *"，注意time是linux中的crontab类型。
    比如
    1. 用户输入“帮我查询最近GPT相关的新闻最近10条，每天晚上6点半发给我”，则输出 ```json {json_text1}```；
    2. 用户输入“我想了解巴以冲突和朝鲜半岛的新闻，每隔一小时和晚上7点半通知我”，则输出 ```json {json_text2}```；
    现在用户输入```{query}```，请回答。
    """
        content = prompt.format(query=query, json_example=json_example, json_text1=json_text1, json_text2=json_text2)
        resp = await self._aask(content)
        res = self.parse_code(resp)
        res_json = json.loads(res)
        return [] if not res_json["words"] else res_json
   
   def parse_code(self, rsp):
        pattern = r'```json(.*)```'
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        code_text = code_text.strip()
        code_text = code_text.replace('\n', '')
        code_text = code_text.replace('\'', '')
        return code_text


class AnalysisOSSRanking(Action):
    async def run(self, msg: str):
        if not isinstance(msg, list):
            data = ast.literal_eval(msg)
        res = []
        for item in data:
            formatted_item = f"""<h3><a href="{item['url']}" target="_blank">{item['title']}</a></h3>
                                <p><b>摘要：</b>{item['description'] if item['description'] else item['title']}</p>
                                <p><b>来源：</b>{item['extra'] if item['extra'] else "无"}</p>
                                <p><b>发布时间：</b>{item['time']}</p>
                            """
            res.append(formatted_item)
        return "[]" if not data else ''.join(res),


class WxPusherClient(Action):
    async def run(self, msg):
        # uids=["UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"]
        uids = await self.get_uids()
        word = memory.messages[-1].content
        summary = f"您订阅的关键词是：{word}"
        data = ast.literal_eval(msg)
        content = data[0]
        if msg:
            await self.send_message(content=content, summary=summary, content_type=2, uids=uids)
        else:
            logger.warning("WxPusherClient content empty!")
            content = "对不起，您订阅的关键词暂无搜索内容"
            await self.send_message(content=content, summary=summary, content_type=2, uids=uids)
        return True

    async def get_uids(self):
        # uids=["UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"]
        # return uids
        url = f"https://wxpusher.zjiecode.com/api/fun/wxuser/v2?appToken={weixinpush_token}"
        async with aiohttp.ClientSession() as session:
            async with session.request("GET", url) as response:
                response.raise_for_status()
                data = await response.json()
        uids = []
        if data:
            uids = [item["uid"] for item in data["data"]["records"]]
        return uids
    

    async def send_message(
        self,
        content,
        summary: Optional[str] = None,
        content_type: int = 1,
        topic_ids: Optional[list[int]] = None,
        uids: Optional[list[int]] = None,
        verify: bool = False,
        url: Optional[str] = None,
    ):
        payload = {
            "appToken": weixinpush_token,
            "content": content,
            "summary": summary,
            "contentType": content_type,
            "topicIds": topic_ids or [],
            "uids": uids,
            "verifyPay": verify,
            "url": url,
        }
        url = f"{weixinpush_base_url}/api/send/message"
        return await self._request("POST", url, json=payload)

    async def _request(self, method, url, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
    
    memory.clear()


# Trigger
class OssInfo(BaseModel):
    timestamp: float = Field(default_factory=time.time)


class RankingCronTrigger:
    def __init__(
        self,
        spec: str,
        tz: Optional[BaseTzInfo] = None,
    ) -> None:
        self.crontab = crontab(spec, tz=tz)

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.crontab.next()
        return Message(self.url, OssInfo())
    

async def wxpusher_callback(msg: Message):
    client = WxPusherClient()
    await client.send_message(msg.content, content_type=3, uids=["UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"])


# Role实现
class OssWatcher(Role):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._init_actions([CrawlOSSRanking, AnalysisOSSRanking, WxPusherClient])
        self._set_react_mode(react_mode="by_order")

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: ready to {self.rc.todo}")
        todo = self.rc.todo
        msg = self.get_memories(k=1)[0]  # find the most k recent messages
        result = await todo.run(msg.content)
        msg = Message(content=str(result), role=self.profile, cause_by=type(todo))
        self.rc.memory.add(msg)
        return msg
    
# 运行入口，
async def main(spec: str = "10 * * * *", discord: bool = False, wxpusher: bool = True):
    callbacks = []
    if wxpusher:
        callbacks.append(wxpusher_callback)

    if not callbacks:
        async def _print(msg: Message):
            print(msg.content)
        callbacks.append(_print)

    async def callback(msg):
        await asyncio.gather(*(call(msg) for call in callbacks))

    runner = SubscriptionRunner()
    await runner.subscribe(OssWatcher(), RankingCronTrigger(spec), callback)
    await runner.run()


if __name__ == "__main__":
    query = "帮我订阅大语言模型的新闻，要最近20条，每天晚上8点发给我"
    oss = OssWatcher()
    result = asyncio.run(oss.run(query))
    logger.info(result)

    # CrawlOSSRanking()


    # import fire
    # fire.Fire(main)
