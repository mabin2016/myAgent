import asyncio
import os
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional, List

import ast
from datetime import datetime
import re
import json

import os
import sys
root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root)

from metagpt.actions.action import Action
from metagpt.roles import Role
from metagpt.roles.role import RoleReactMode
from metagpt.logs import logger
from job.utils.amap import TrainTicketService, AmapWeather, AmapPOISearch
from metagpt.schema import Message
from job.utils.util import generate_dates


PROMPT_ENTITY = """
你是一个命名实体识别专家，用户输入自然语言，你从中提取出命名实体并将结果以json的形式返回，
在返回结果时，保持准确性和简洁性，同时遵循指定的json格式：
```json
{
	"source_city": "北京",
	"dest_city": "上海",
	"some_date": "今天的日期",
	"has_weather": 1,
	"has_trans": 1,
	"keywords": ["娱乐", "酒店"]
}
```
## 要求
- 如果用户没有明确指出source_city，这source_city留空
- 如果用户没有明确指定日期,则some_date默认是今天的日期
- 如果用户的输入中只有一个城市，则dest_city是用户指定的城市，如果没有提到任何城市，则默认留空
- 如果用户提到天气，则has_weather是1，否则是0
- 如果用户提到交通，则has_trans是1，否则是0
- 如果用户没有提到时间，则some_date留空
- 如果有识别到用户想出行的意图，比如“去哪里“的意思表示，并且没有指明起始地点，则source_city是"广州"
- 如果用户没有提到任何关键字，则keywords是["美食", "逛街", "购物", "娱乐"]
- 对于用户指定的日期，你可以编写代码获取，比如用户输入"我想明天去看雪"，这你可以写类似代码获取到明天的日期
```python
from datetime import datetime, timedelta
# 获取当前日期和时间
now = datetime.now()
# 计算明天的日期
tomorrow = now + timedelta(days=1)
# 打印明天的日期
print(tomorrow.strftime('%Y-%m-%d'))
```
	
## 举例
- 用户输入“我想明天去上海，帮我看下还有哪趟高铁有票，并且看下百色的天气如何，有哪些好玩的”，则输出 
```json
{
	"source_city": "北京",
	"dest_city": "上海",
	"some_date": "明天的日期",
	"has_weather": 1,
	"has_trans": 1,
	"keywords": ["娱乐"]
}
```
- 用户输入“北京有什么好玩的，不知道会不会下雪”，则输出
```json
{
	"source_city": "",
	"dest_city": "北京",
	"some_date": "",
	"has_weather": 1,
	"has_trans": 0,
	"keywords": ["娱乐"]
}
```
- 用户输入“上海迪斯尼好玩吗，从广州过去方便不”，则输出
```json
{
	"source_city": "广州",
	"dest_city": "上海",
	"some_date": "",
	"has_weather": 0,
	"has_trans": 1,
	"keywords": ["娱乐", "迪斯尼"]
}
```
- 用户输入“百色哪一家烧烤店最好吃，现在过去交通拥堵吗”，则输出
```json
{
	"source_city": "",
	"dest_city": "百色",
	"some_date": "",
	"has_weather": 0,
	"has_trans": 1,
	"keywords": ["烧烤"]
}
```
- 用户输入“百色右江区有7天连锁酒店吗，在哪里”，则输出
```json
{
	"source_city": "",
	"dest_city": "百色",
	"some_date": "",
	"has_weather": 0,
	"has_trans": 0,
	"keywords": ["7天连锁酒店"]
}
```
- 用户输入“我想去看雪，有什么推荐的吗”，则输出
```json
{
	"source_city": "",
	"dest_city": "",
	"some_date": "",
	"has_weather": 0,
	"has_trans": 0,
	"keywords": []
}
```
- 用户输入“我想明天去百色，有什么推荐的吗”，则输出
```json
{
	"source_city": "广州",
	"dest_city": "百色",
	"some_date": "明天的日期",
	"has_weather": 0,
	"has_trans": 0,
	"keywords": []
}
- 用户输入“我想2024年2月20日去百色，有什么推荐的吗”，则输出
```json
{
	"source_city": "广州",
	"dest_city": "百色",
	"some_date": "2024-02-10",
	"has_weather": 0,
	"has_trans": 0,
	"keywords": []
}
```
现在用户输入```text {{query}}```，请回答。
"""


PROMPT_SUMMARY = """
你是一名出行达人，也是一名NLP专家，请给我总结以下文本和用户的输入内容，生成一份通俗易懂的自然语言，如果文本为空则不需要总结。

## 天气类
### 给定文本
```json
{{resp_weather}}
```
#### 要求
- 根据给定文本总结天气情况并给出建议

## 周边娱乐餐饮景点类
### 给定文本
```json
{{resp_keywords}}
```
#### 要求
- 给定文本有多少段就给出多少段建议，每段建议遵循下面规则：给定文本中cost表示人均消费水平，rating表示评分，请根据这两个字段给出每段文本中性价比最高的8个，然后再给出建议，并附上地址、电话等信息

## 火车票类
### 给定的火车票信息
```json
{{resp_ticket}}
```
#### 要求9
- 根据给定的火车票信息列出最具性价比的5条信息，并做出总结和建议，如果给定的信息为空则不输出内容

## 用户输入的内容是
```text
{{query}}
```
请结合以上输出给出建议。
"""

class GetTransInfo(Action):
    """获取交通、天气、周边、火车票信息并总结
    """
    async def run(self, msgs):
        msg = msgs[-1].content
        try:
            content = ast.literal_eval(msg)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            return Message(content="解析失败")
            
        source_city = content["source_city"]
        dest_city = content["dest_city"]
        keywords = content["keywords"]
        some_date = content["some_date"] if content["some_date"] else str(datetime.today().date())
        if dest_city:
            resp_weather = ""
            resp_keywords = ""
            if content["has_weather"] == 1:
                weather = AmapWeather()
                resp_weather = weather.get_weather(dest_city)

            if keywords:
                poi_search = AmapPOISearch()
                resp_keywords = []
                for keyword in keywords:
                    result = poi_search.search(keyword, dest_city)
                    if result:
                        result = [{
                            "address": item["address"],
                            "biz_ext": item["biz_ext"],
                            "type": item["type"],
                            "adname": item["adname"],
                            "name": item["name"],
                            "tel": item["tel"],
                                } for item in result["pois"]]
                        tmpl = f"""
                            ```json
                                {result}
                            ```
                        """
                        resp_keywords.append(tmpl)

            resp_ticket = ""
            dates = ""
            if source_city and dest_city:
                dates = generate_dates(datetime.now().date(), 10)
                resp_ticket = await self.request_resp_ticket_api(source_city, dest_city, dates)
    
        # print(resp_weather)
        # print("\r\n\r\n")
        # print(resp_keywords)
        # print("\r\n\r\n")
        # print(resp_ticket)
        # print("\r\n\r\n")
        # resp = f"""{resp_weather}\r\n{resp_keywords}\r\n{resp_ticket}"""
        prompt = PROMPT_SUMMARY.replace("{{resp_weather}}", str(resp_weather))\
            .replace("{{resp_keywords}}", str(resp_keywords))\
            .replace("{{resp_ticket}}", str(resp_ticket))\
            .replace("{{query}}", msgs[0].content)
        content = await self._aask(prompt)
        return Message(content=content)
    
    async def request_resp_ticket_api(self, source_city: str, dest_city: str, dates: List):
        service = TrainTicketService()
        tickets_info = ""
        # 查找10天内的火车票
        for _date in dates:
            tickets_info = service.get_tickets(dest_city, source_city, _date)
            if tickets_info and tickets_info["data"]["count"] > 0:
                break
        return str(tickets_info["data"]["list"])
    
    async def resp_ticket_summary(self, tickets_info: str, dest_city: str, source_city: str, some_date: str):
        if not tickets_info:
            return ""
        # return tickets_info
        prompt = f"""
        你是一位信息处理专家，这里有一个从{dest_city}到{source_city}的火车票信息，时间是{some_date}，内容如下
        ```json
            {tickets_info}
        ```
        请给我用自然语言总结出最合适的价格、座位、时长、发车时间的信息并提供建议，注意不要罗列说给的内容，只要总结即可。
        """
        resp = await self._aask(prompt)
        return resp

class getEntity(Action):
    """获取用户意图
    """

    async def run(self, msgs: str = ""):
        content = msgs[-1].content
        res = await self.detect_entity(content)
        return Message(str(res))
    
    async def detect_entity(self, query):
        prompt = PROMPT_ENTITY.replace("{{query}}", query)
        # logger.info(f"PROMPT_ENTITY: {prompt}")
        resp = await self._aask(prompt)
        res = self.parse_code(resp)
        try:
            json_data = ast.literal_eval(res)
        except Exception as e:
            logger.error(f"Error parsing JSON: {e}")
            json_data = {
                    "source_city": "",
                    "dest_city": "",
                    "some_date": "",
                    "has_weather": 0,
                    "has_trans": 0,
                    "keywords": [],
            }
        return json_data
   
    def parse_code(self, rsp):
        pattern = r'```json(.*)```'
        match = re.search(pattern, rsp, re.DOTALL)
        code_text = match.group(1) if match else rsp
        code_text = code_text.strip()
        code_text = code_text.replace('\n', '')
        code_text = code_text.replace('\'', '')
        return code_text


class Traveler(Role):
    name: str = "Traveler"
    profile: str = "Give Travel Advising"
    goal: str = "Fetch weatcher, train resp_tickets information and other keywords related to the journey"
    constraints: str = "The suggestion should be clear, effection and safe"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._init_actions([getEntity, GetTransInfo])
        self._set_react_mode(react_mode=RoleReactMode.BY_ORDER)

    async def _react(self) -> Message:
        while True:
            await self._think()
            if self.rc.todo is None:
                break

            msg = await self._act()
            if msg:
                yield msg
    async def react(self) -> Message:
        from metagpt.roles.role import RoleReactMode
        if self.rc.react_mode == RoleReactMode.REACT:
            rsp = self._react()
        elif self.rc.react_mode == RoleReactMode.BY_ORDER:
            rsp = await self._act_by_order()
        elif self.rc.react_mode == RoleReactMode.PLAN_AND_ACT:
            rsp = await self._plan_and_act()
        self._set_state(state=-1)  # current reaction is complete, reset state to -1 and todo back to None
        yield rsp

    async def run(self, with_message=None):
        if with_message:
            msg = Message(content=with_message)
            self.put_message(msg)

        if not await self._observe():
            logger.warning(f"{self._setting}: no news. waiting.")
            yield

        async for msg in self.react():
            yield msg.content

        self.rc.todo = None
        # self.publish_message(self.total_content)

async def main(msg: str = ""):
    role = Traveler()
    result = role.run(msg)
    async for msg in result:
        print(f"msg: {msg}")

if __name__ == "__main__":
    # content = {
    #     "source_city": "广州",
    #     "dest_city": "百色",
    #     "some_date": "",
    #     "has_weather": 1,
    #     "keywords": ["烧烤", "酒店"]
    #     # "keywords": []
    # }
    # ts = GetTransInfo()
    # res = asyncio.run(ts.run(content))

    # query = "我想明天去百色，帮我看下还有哪趟高铁有票，并且看下百色的天气如何，有哪些好玩的"
    query = "我想去新疆看雪，吃烤肉串，不知道现在那边有没有下雪，现在抢票难吗"
    # query = "百色有哪些好玩的"
    # ts = getEntity()
    # res = asyncio.run(ts.run(query=query))

    result = asyncio.run(main(query))

    

