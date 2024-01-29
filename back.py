import uvicorn
import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import time
from datetime import datetime
import pydantic
from pydantic import BaseModel
from typing import (
    Any,
)

from job import nora_oss as _nora_oss
from job.nora_article import TutorialAssistant
from job import nora_keyword as _nora_keyword


# from job.oss_action_node import memory

app = FastAPI()
app.global_uid = None
app.qrcode = None

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class Data(BaseModel):
    appId: int
    appKey: str = None  # 可能会删除，设置为可选
    appName: str
    source: str
    userName: str = None  # 新用户微信不再返回，设置为可选
    userHeadImg: str = None  # 新用户微信不再返回，设置为可选
    time: int
    uid: str
    extra: str = None  # 扫描默认二维码为空，设置为可选

class WeixinMessage(BaseModel):
    action: str
    data: Data

@app.post("/weixin_pusher_uuid_callback")
async def weixin_pusher_uuid_callback(request: WeixinMessage):
    try:
        # print(request.data.uid)
        app.global_uid = request.data.uid
        return {"status": "success", "uid": request.data.uid}
    except HTTPException as e:
        raise e

@app.get("/nora_article")
async def generate_document(msg: str = ""):
    # msg = "给我写一份mongodb教程"
    async def generate():
        role = TutorialAssistant()
        result = role.run(msg)
        yield f"""下载地址：http://119.23.242.207/files/{datetime.now().strftime("%Y%m%d")}\r\n"""
        async for item in result:
            yield item
        yield f"""生成结束，请到http://119.23.242.207/files/{datetime.now().strftime("%Y%m%d")}下载"""
        
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/nora_keyword")
async def nora_keyword(msg: str = ""):
    asyncio.gather(_nora_keyword.run(msg))
    return "已执行，稍后请查看您的微信消息"

@app.get("/nora_oss")
async def nora_oss(msg: str = ""):
    asyncio.gather(_nora_oss.run(msg))
    return "已执行，需要几分钟，稍后请查看您的微信消息"

@app.get("/nora_travel")
async def nora_travel(msg: str = ""):
    return "旅游胜地介绍接口"



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)