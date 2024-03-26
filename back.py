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

#from job import nora_oss as _nora_oss
from job import nora_keyword as _nora_keyword
from job.nora_article import TutorialAssistant
from job.nora_travel import Traveler


# from job.oss_action_node import memory

app = FastAPI()
app.global_uid = None
app.qrcode = None

from fastapi import FastAPI


@app.get("/nora_article")
async def generate_document(msg: str = "", mail: str = ""):
    # msg = "给我写一份mongodb教程"
    async def generate():
        role = TutorialAssistant()
        result = role.run(msg)
        yield f"""下载地址：http://119.23.242.207/files\r\n"""
        async for item in result:
            yield item
        yield f"""生成结束，请查看 http://119.23.242.207/files"""
        
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/nora_keyword")
async def nora_keyword(msg: str = "", mail: str = ""):
    asyncio.gather(_nora_keyword.run(msg, mail))
    return "已执行，需要几分钟，稍后请查收您的邮件"

#@app.get("/nora_oss")
#async def nora_oss(msg: str = "", mail: str = ""):
#    asyncio.gather(_nora_oss.run(msg, mail))
#    return "已执行，需要几分钟，稍后请查收您的邮件"

@app.get("/nora_travel")
async def nora_travel(msg: str = "", mail: str = ""):
    async def generate():
        role = Traveler()
        result = role.run(msg)
        async for item in result:
            yield item
    return StreamingResponse(generate(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
