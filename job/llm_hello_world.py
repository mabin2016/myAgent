#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

from metagpt.llm import LLM
from metagpt.logs import logger

prompt = """
你是一个命名实体识别模型，用户输入自然语言，你从中提取出命名实体并将结果以json的形式返回，在返回结果时，我会保持准确性和简洁性，同时遵循用户指定的json格式：```["words": ["实体1", "实体2"], "num": 数字, "time": [时间点1, 时间点2]]```，如果用户没有指定num和time则num=10，time=9。
比如用户输入“帮我查询最近GPT相关的新闻最近10条，每天早上9点和晚上6点半发给我”，则输出 ```json ["words": ["GPT"], "num", "time": [6, 18:30]] ```，现在用户输入````{query}```，请回答。
"""

async def main():
    llm = LLM()
    query = "帮我订阅openai和台湾选举的新闻，每天晚上8点发给我"
    content = prompt.format(query=query)
    # logger.info(await llm.aask("hello world"))
    # logger.info(await llm.aask_batch(["hi", "write python hello world."]))

    hello_msg = [{"role": "user", "content": content}]
    # logger.info(await llm.acompletion(hello_msg))
    logger.info(await llm.acompletion_text(hello_msg))

    # streaming mode, much slower
    # await llm.acompletion_text(hello_msg, stream=True)

    # check completion if exist to test llm complete functions
    # if hasattr(llm, "completion"):
    #     logger.info(llm.completion(hello_msg))


if __name__ == "__main__":
    asyncio.run(main())
