import asyncio
import sys
from typing import Optional
from uuid import uuid4
import ast
import traceback
import re
from aiocron import crontab

import os
import sys
root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root)

from metagpt.team import Team
from metagpt.actions import UserRequirement
from metagpt.actions.action import Action
from metagpt.actions.action_node import ActionNode
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.tools.web_browser_engine import WebBrowserEngine
from metagpt.utils.common import CodeParser, any_to_str
from metagpt.utils.parse_html import _get_soup
from metagpt.logs import logger
from pytz import BaseTzInfo
from langchain_community.chat_message_histories import SQLChatMessageHistory
from job.utils.util import wxpusher_callback


from job.utils.util import get_cron

user_session_id = uuid4().hex
memory = SQLChatMessageHistory(session_id=user_session_id, connection_string="sqlite:///sqlite.db")
memory.clear()

global global_mail

# 先写NODES
LANGUAGE = ActionNode(
    key="Language",
    expected_type=str,
    instruction="Provide the language used in the project, typically matching the user's requirement language.",
    example="en_us",
)

CRON_EXPRESSION = ActionNode(
    key="Cron Expression",
    expected_type=str,
    instruction="If the user requires scheduled triggering, please provide the corresponding 5-field cron expression. "
    "Otherwise, let it blank.",
    example="",
)

CRAWLER_URL_LIST = ActionNode(
    key="Crawler URL List",
    expected_type=list[str],
    instruction="List the URLs user want to crawl. Leave it blank if not provided in the User Requirement.",
    example=["https://example1.com", "https://example2.com"],
)

PAGE_CONTENT_EXTRACTION = ActionNode(
    key="Page Content Extraction",
    expected_type=str,
    instruction="Specify the requirements and tips to extract from the crawled web pages based on User Requirement.",
    example="Retrieve the titles and content of articles published today.",
)

CRAWL_POST_PROCESSING = ActionNode(
    key="Crawl Post Processing",
    expected_type=str,
    instruction="Specify the processing to be applied to the crawled content, such as summarizing today's news.",
    example="Generate a summary of today's news articles.",
)

INFORMATION_SUPPLEMENT = ActionNode(
    key="Information Supplement",
    expected_type=str,
    instruction="If unable to obtain the Cron Expression, prompt the user to provide the time to receive subscription "
    "messages. If unable to obtain the URL List Crawler, prompt the user to provide the URLs they want to crawl. Keep it "
    "blank if everything is clear",
    example="",
)

NODES = [
    LANGUAGE,
    CRON_EXPRESSION,
    CRAWLER_URL_LIST,
    PAGE_CONTENT_EXTRACTION,
    CRAWL_POST_PROCESSING,
    INFORMATION_SUPPLEMENT,
]

PARSE_SUB_REQUIREMENTS_NODE = ActionNode.from_children("ParseSubscriptionReq", NODES)

PARSE_SUB_REQUIREMENT_TEMPLATE = """
### User Requirement
{requirements}
"""

PROMPT_TEMPLATE = """Please complete the web page crawler parse function to achieve the User Requirement. The parse \
function should take a BeautifulSoup object as input, which corresponds to the HTML outline provided in the Context.\
When analyzing the provided context, please pay attention to whether there is a standard time format included. \
If such a time indicator is not found, please omit the extraction step for the time field in the relevant code.
If the time shows like '秒前' or '分钟前' or '小时前' or '昨天',do not deal with it and show the original format.
If there is the time field, strictly let it be the last field of the extracted data.

```python
from bs4 import BeautifulSoup

# only complete the parse function
def parse(soup: BeautifulSoup):
    ...
    # Return the object that the user wants to retrieve, don't use print
```

## User Requirement
{requirement}

## Context

The outline of html page to scrape is show like below:

```tree
{outline}
```
"""


def parse_code(rsp):
    pattern = r'```html(.*)```'
    match = re.search(pattern, rsp, re.DOTALL)
    code_text = match.group(1) if match else rsp
    code_text = code_text.strip()
    code_text = code_text.replace('\n', '')
    code_text = code_text.replace('\t', '')
    code_text = code_text.replace('\'', '')
    return code_text

def parse_user_msg(msg):
    pattern = r'\[CONTENT\](.*?)\[/CONTENT\]'
    match = re.search(pattern, msg, re.DOTALL)
    res = match.group(1) if match else msg
    res = res.strip().replace('\n', '').replace('\t', '')
    return res

def parse_json2html(content):
    html = ''
    if not isinstance(content, list):
        try:
            json_data = ast.literal_eval(content)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
    else:
        json_data = content
    if not json_data:
        return html
    
    fields = list(json_data[0].keys())
    # 将包含"time"字眼的字段移至列表末尾
    time_fields = [field for field in fields if "time" in field or "date" in field]
    non_time_fields = [field for field in fields if field not in time_fields]
    # 重新排序字段列表
    fields = non_time_fields + time_fields

    for item in json_data:
        html += '<div>'
        for i, field in enumerate(fields):
            if i == 0:
                html += '<h3>{}</h3>'.format(item[field])
            else:
                html += '<p><b>{}</b>：{}</p>'.format(field, item[field])
        html += '</div>'
    return html

# 辅助函数: 获取html css大纲视图
def get_outline(page):
    soup = _get_soup(page.html)
    outline = []

    def process_element(element, depth):
        name = element.name
        if not name:
            return
        if name in ["script", "style"]:
            return

        element_info = {"name": element.name, "depth": depth}

        if name in ["svg"]:
            element_info["text"] = None
            outline.append(element_info)
            return

        element_info["text"] = element.string
        # Check if the element has an "id" attribute
        if "id" in element.attrs:
            element_info["id"] = element["id"]

        if "class" in element.attrs:
            element_info["class"] = element["class"]
        outline.append(element_info)
        for child in element.children:
            process_element(child, depth + 1)

    try:
        for element in soup.body.children:
            process_element(element, 1)
    except AttributeError as e:
        logger.warning(f"soup.body is NoneType: {e}")
        
    return outline

# 触发器：crontab
class CronTrigger:
    def __init__(self, spec: str, tz: Optional[BaseTzInfo] = None) -> None:
        if not spec:
            spec = get_cron()
        print(f"spec: {spec}")
        self.crontab = crontab(spec, tz=tz)

    def __aiter__(self):
        return self

    async def __anext__(self):
        await self.crontab.next()
        return Message()

# 写爬虫代码的Action
class WriteCrawlerCode(Action):
    async def run(self, requirement):
        requirement: Message = requirement[-1]
        data = requirement.instruct_content.dict()
        urls = data["Crawler URL List"]
        query = data["Page Content Extraction"]

        codes = {}
        for url in urls:
            codes[url] = await self._write_code(url, query)
        return "\n".join(f"# {url}\n{code}" for url, code in codes.items())

    async def _write_code(self, url, query):
        page = await WebBrowserEngine().run(url)
        # code = CodeParser.parse_code(block="")
        code = ""
        outline = get_outline(page)
        if outline:
            outline = "\n".join(
                f"{' '*i['depth']}{'.'.join([i['name'], *i.get('class', [])])}: {i['text'] if i['text'] else ''}"
                for i in outline
            )
            code_rsp = await self._aask(PROMPT_TEMPLATE.format(outline=outline, requirement=query))
            code = CodeParser.parse_code(block="", text=code_rsp)
        return code


# 分析订阅需求的Action
class ParseSubRequirement(Action):
    async def run(self, requirements):
        requirements = "\n".join(i.content for i in requirements)
        context = PARSE_SUB_REQUIREMENT_TEMPLATE.format(requirements=requirements)
        node = await PARSE_SUB_REQUIREMENTS_NODE.fill(context=context, llm=self.llm)
        memory.add_user_message(node.content)
        return node
    

# 运行订阅智能体的Action
# class RunSubscription(Action):
#     async def run(self, msgs):
#         from metagpt.roles.role import Role
#         from metagpt.subscription import SubscriptionRunner

#         code = msgs[-1].content
#         print(f"code {code}")
#         req = msgs[-2].instruct_content.dict()
#         urls = req["Crawler URL List"]
#         process = req["Crawl Post Processing"]
#         spec = req["Cron Expression"]
#         SubAction = self.create_sub_action_cls(urls, code, process)
#         SubRole = type("SubRole", (Role,), {})
#         role = SubRole()
#         role.init_actions([SubAction])
#         runner = SubscriptionRunner()

#         async def callback(msg):
#             if msg:
#                 content = msg.content
#                 print(content)
#             else:
#                 content = "由于网站过于复杂，抓取失败"
                
#             user_msg = parse_user_msg(memory.messages[-1].content)
#             user_requirement = ast.literal_eval(user_msg)
#             summary = f"""{user_requirement['Page Content Extraction']}， {user_requirement['Crawl Post Processing']}"""
#             # await wxpusher_callback(content, summary=summary)

              # from job.utils.mail import EmailSender
#             global global_mail
#             mail = EmailSender()
#             await mail.send_email(recipient=global_mail, subject=content, body=summary)
            
#         await runner.subscribe(role, CronTrigger(spec), callback)
#         await runner.run()

#     def create_sub_action_cls(self, urls: list[str], code: str, process: str):
#         modules = {}
#         for url in urls[::-1]:
#             code, current = code.rsplit(f"# {url}", maxsplit=1)
#             name = uuid4().hex
#             module = type(sys)(name)
#             exec(current, module.__dict__)
#             modules[url] = module

#         class SubAction(Action):
#             async def run(self, *args, **kwargs):
#                 pages = await WebBrowserEngine().run(*urls)
#                 if len(urls) == 1:
#                     pages = [pages]
#                 try:
#                     data = []
#                     for url, page in zip(urls, pages):
#                         data.append(getattr(modules[url], "parse")(page.soup))

#                     return parse_json2html(data[0])
#                 except Exception as e:
#                     print(traceback.format_exc())
#                     traceback.print_exc()
#                     return "爬取失败"

#         return SubAction


class SendWein(Action):
    async def run(self, msgs):
        code = msgs[-1].content
        req = msgs[-2].instruct_content.dict()
        urls = req["Crawler URL List"]

        modules = {}
        for url in urls[::-1]:
            code, current = code.rsplit(f"# {url}", maxsplit=1)
            name = uuid4().hex
            module = type(sys)(name)
            exec(current, module.__dict__)
            modules[url] = module

        pages = await WebBrowserEngine().run(*urls)
        if len(urls) == 1:
            pages = [pages]
        try:
            data = []
            for url, page in zip(urls, pages):
                data.append(getattr(modules[url], "parse")(page.soup))
            msg = parse_json2html(data[0])
        except Exception as e:
            print(traceback.format_exc())
            traceback.print_exc()
            msg = "爬取失败"
            logger.error(traceback.format_exc())

        if not msg:
            msg = "暂无消息"

        logger.info(f"send mail: {msg}")
        # user_msg = parse_user_msg(memory.messages[-1].content)
        # user_requirement = ast.literal_eval(user_msg)
        # await wxpusher_callback(msg, summary=summary)
        summary = f"""爬取的网站地址:{urls[0]}"""
        
        from job.utils.mail import EmailSender
        mail = EmailSender()
        
        await mail.send_email(recipient=global_mail, subject=summary, body=msg)
        return Message()


# 定义爬虫工程师角色
class CrawlerEngineer(Role):
    name: str = "John"
    profile: str = "Crawling Engineer"
    goal: str = "Write elegant, readable, extensible, efficient code"
    constraints: str = "The code should conform to standards like PEP8 and be modular and maintainable"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._init_actions([WriteCrawlerCode])
        self._watch([ParseSubRequirement]) # 意思是WriteCrawlerCode跟在ParseSubRequirement执行


# 定义订阅助手角色
class SubscriptionAssistant(Role):
    """Analyze user subscription requirements."""

    name: str = "Grace"
    profile: str = "Subscription Assistant"
    goal: str = "analyze user subscription requirements to provide personalized subscription services."
    constraints: str = "utilize the same language as the User Requirement"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # self._init_actions([ParseSubRequirement, RunSubscription])
        self._init_actions([ParseSubRequirement, SendWein])
        
        # 这里添加watch后_observe()会观察到并记录到self.rc.watch，run()的时候会回判断_observe()返回值大于0则继续执行
        self._watch([UserRequirement, WriteCrawlerCode])

    async def _think(self) -> bool:
        cause_by = self.rc.history[-1].cause_by
        # 这里state设置完之后的运行流程是 UserRequirement -> UserRequirement -> WriteCrawlerCode(因为CrawlerEngineer这个类watch了ParseSubRequirement：self._watch([ParseSubRequirement])) -> SendWein
        if cause_by == any_to_str(UserRequirement):
            state = 0
        elif cause_by == any_to_str(WriteCrawlerCode):
            state = 1

        # 当前的statte等于修改后的state，说明已经执行过这个todo，不需要再执行了
        if self.rc.state == state:
            self.rc.todo = None
            return False
        self._set_state(state)
        return True


async def run(query: str = "", mail: str = ""):
    if not query:
        query = "从https://pitchhub.36kr.com/investevent爬取信息，获取融资时间，项目名称，所属行业，融资轮次，融资金额，投资方，详情链接字段，然后发给我"
    
    logger.info(f"query: {query}")
    
    global_mail = mail
    
    team = Team()
    team.hire([SubscriptionAssistant(), CrawlerEngineer()])
    team.run_project(query)
    await team.run()
    logger.info(f"finish!")

if __name__ == "__main__":
    result = asyncio.run(run())
    # from metagpt.schema import Message
    # asyncio.run(ParseSubRequirement().run([Message(
    #     "从36kr创投平台https://pitchhub.36kr.com/financing-flash 爬取所有初创企业融资的信息，获取标题，链接， 时间，总结今天的融资新闻，然后在晚上七点半送给我"
    # )]))

    