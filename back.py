import uvicorn
import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
import time
import pydantic
from pydantic import BaseModel
from typing import (
    Any,
)

from job import nora_oss as _nora_oss
from job import nora_article as _nora_article
from job import nora_keyword as _nora_keyword


# from job.oss_action_node import memory

app = FastAPI()
from fastapi import FastAPI

app = FastAPI()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class BaseResponse(BaseModel):
    code: int = pydantic.Field(200, description="API status code")
    msg: str = pydantic.Field("success", description="API status message")
    data: Any = pydantic.Field(None, description="API data")

    class Config:
        schema_extra = {
            "example": {
                "code": 200,
                "msg": "success",
            }
        }

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
        print(request.data.uid)
        return {"status": "success", "uid": request.data.uid}
    except HTTPException as e:
        raise e

@app.get("/nora_article")
async def generate_document(msg: str = ""):
    # res = asyncio.gather(_nora_article.run(msg))
    async def generate():
        for item in _nora_article.run(msg):
            yield item
            time.sleep(1)
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/nora_article2")
async def generate_document(msg: str = ""):
    res = asyncio.gather(_nora_article.run(msg))
    # print(res)
    # res = await _nora_article(msg)
    # print(res)
    # return res
    # response = Response()
    # for item in res:
    #     response.content.append(item)
    #     await response.prepare(None)
    async for token in res.aiter():
        yield token
    # return BaseResponse(code=200, msg=f"sss")
    # return res
    # return "文档生成中...，需要几分钟，请移步链接查看结果 http://119.23.242.207/tutorial_docx"

@app.get("/nora_keyword")
async def nora_keyword(msg: str = ""):
    asyncio.gather(_nora_keyword.run(msg))
    return "已执行，稍后请查看您的微信消息"

@app.get("/nora_oss")
async def nora_oss(msg: str = ""):
    asyncio.gather(_nora_oss.run(msg))
    return "已执行，稍后请查看您的微信消息"

@app.get("/nora_travel")
async def travel_dest(msg: str = ""):
    return "旅游胜地介绍接口"



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)