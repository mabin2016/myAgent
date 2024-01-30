from datetime import datetime, timedelta
from croniter import croniter
from typing import Optional
import asyncio
import aiohttp
from aiocron import crontab
from pydantic import BaseModel, Field

from metagpt.logs import logger
from metagpt.schema import Message
from metagpt.config import CONFIG


    
class WxPusherClient:
    def __init__(self):
        self.token = CONFIG.WEINXINPUSHER_TOKEN

    async def send_message(
        self,
        content,
        summary: Optional[str] = None,
        weixin_uids: list[str] = ["UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"],
        content_type: int = 3,
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
            "uids": weixin_uids, 
            "verifyPay": verify,
            "url": url,
        }
        url = f"http://wxpusher.zjiecode.com/api/send/message"
        return await self._request("POST", url, json=payload)

    async def qrcode_with_param(self):
        """
        生成带参数二维码
        """
        payload = {
            "appToken": self.token,
            "extra": CONFIG.WEINXINPUSHER_QRCODE,
            "validTime": 30 * 24 * 60 * 60
        }
        url = f"https://wxpusher.zjiecode.com/api/fun/create/qrcode"
        return await self._request("POST", url, json=payload)
    
    async def get_last_scan_uid(self):
        url = f"https://wxpusher.zjiecode.com/api/fun/scan-qrcode-uid?code={CONFIG.WEINXINPUSHER_QRCODE}"
        return await self._request("GET", url)

    async def _request(self, method, url, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()

async def wxpusher_callback(msg: str, summary: str):
    client = WxPusherClient()
    res = await client.get_last_scan_uid()
    weixin_uids = [res["data"]] if res["data"] else ["UID_KS1zPtgrFyzPGTuyJxvHlrDXsiiz"]
    logger.info(f"summary: {summary} weixin_uids: {weixin_uids}")
    await client.send_message(msg, summary=summary, weixin_uids=weixin_uids)

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

def generate_dates(start_date, days):
    date_list = []
    for i in range(days):
        date_list.append((start_date + timedelta(days=i)).strftime('%Y-%m-%d'))
    return date_list

if __name__ == "__main__":
    # res = get_cron()
    # print(res)
    wx = WxPusherClient()
    res = asyncio.run(wx.get_last_scan_uid())
    # uid = asyncio.run(wx.qrcode_with_param())
    # print(f"uid: {res["data"]}")
