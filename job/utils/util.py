
from datetime import datetime, timedelta
from croniter import croniter
from typing import Optional

import aiohttp
from aiocron import crontab
from pydantic import BaseModel, Field

from metagpt.logs import logger
from metagpt.schema import Message

    
class WxPusherClient:
    def __init__(self, token: Optional[str] = "AT_A33lVU9Ksx4qUEZRHlWa54MmsU78VMmy", base_url: str = "http://wxpusher.zjiecode.com"):
        self.base_url = base_url
        self.token = token

    async def send_message(
        self,
        content,
        summary: Optional[str] = None,
        uids: list[str] = ["UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"],
        content_type: int = 1,
        topic_ids: Optional[list[int]] = None,
        verify: bool = False,
        url: Optional[str] = None,
    ):
        payload = {
            "appToken": self.token,
            "content": content,
            "summary": summary,
            "contentType": content_type,
            "topicIds": topic_ids or [],
            "uids": uids, 
            "verifyPay": verify,
            "url": url,
        }
        url = f"{self.base_url}/api/send/message"
        return await self._request("POST", url, json=payload)

    async def _request(self, method, url, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

async def wxpusher_callback(msg: str, summary: str, content_type: int = 3):
    client = WxPusherClient()
    print(summary)
    await client.send_message(msg, summary=summary, content_type=3)

def get_cron(mins_later: int = 1):
    current_datetime = datetime.now()
    dt = current_datetime + timedelta(minutes=mins_later)
    minute = dt.minute
    hour = dt.hour
    day = dt.day
    month = dt.month
    day_of_week = '*'
    # 组合成cron表达式
    cron_expression = f"{minute} {hour} {day} {month} {day_of_week}"
    return cron_expression


if __name__ == "__main__":
    res = get_cron()
    print(res)
