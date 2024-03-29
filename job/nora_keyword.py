import asyncio
from uuid import uuid4
from typing import List

import aiohttp
import datetime
import re
import json
from langchain_community.chat_message_histories import SQLChatMessageHistory

from metagpt.actions.action import Action
from metagpt.roles import Role
from metagpt.logs import logger
from metagpt.schema import Message
from metagpt.config import CONFIG
#from job.utils.util import wxpusher_callback

#weixin_uids: List[str] = []

user_session_id = uuid4().hex
memory = SQLChatMessageHistory(session_id=user_session_id, connection_string="sqlite:///sqlite.db")
memory.clear()

class CrawlOSSRanking(Action):
   
    query: str = ""

    async def run(self, query: str = ""):
        entitys = await self.detect_entity(query)
        word = entitys["words"][0]
        data = await self.crawl_api(word, entitys["num"])
        msg = self.context2markdown(data)
        # await wxpusher_callback(msg, summary=f"您订阅的关键词是: {word}")

        from job.utils.mail import EmailSender
        receipt_mail = memory.messages[-1].content
        print(f"receipt_mail {receipt_mail}")
        mail = EmailSender()
        print(mail, msg)
        mail.send_email(recipient=receipt_mail, subject=f"您订阅的关键词是: {word}", body=msg)
        
        return Message(msg)
        
    async def crawl_api(self, word: str = "", num: int = 20):
        url = f"https://api.tophubdata.com/search?q={word}"
        async with aiohttp.ClientSession() as client:
            headers = {"Authorization": CONFIG.TOPHUB_TODAY_TOKEN}
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
    你是一个命名实体识别专家，用户输入自然语言，你从中提取出命名实体并将结果以json的形式返回，在返回结果时，我会保持准确性和简洁性，同时遵循用户指定的json格式：```json {json_example}```，
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

    def context2markdown(self, data: list = []):
        def format_to_markdown(item):
            return f"""<h3> <a href="{item['url']}" target="_blank">{item['title']}</a></h3>
        <p>{item['description']}</p>
        <p>{item['extra']}</p>
        <p>{item['time']}</p>"""
        return ''.join(format_to_markdown(item) for item in data)

class OSSKeyword(Role):
    topic: str = "OSSKeyword"
    profile: str = "crawling by keyword"
    goal: str = "crawl data"
    constraints: str = "The results must be string"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._init_actions([CrawlOSSRanking])


async def run(msg: str = "帮我订阅openai和台湾选举的新闻，每天晚上8点发给我", mail: str = ""):
    logger.info(msg)
    memory.add_user_message(mail)
    role = OSSKeyword()
    res = await role.run(msg)
    logger.info(f"finish!")
    return res


if __name__ == "__main__":
    res = asyncio.run(run())
    print(res)

    

