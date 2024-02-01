from datetime import datetime
from typing import Dict
import asyncio

import os
import sys
root = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, root)

from metagpt.actions.write_tutorial import WriteDirectory, WriteContent
from metagpt.const import TUTORIAL_PATH
from metagpt.logs import logger
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.utils.file import File

from typing import Dict

from metagpt.actions import Action
from metagpt.prompts.tutorial_assistant import DIRECTORY_PROMPT, CONTENT_PROMPT
from metagpt.utils.common import OutputParser
from metagpt.utils.common import (
    role_raise_decorator,
)
from metagpt.actions import UserRequirement

class WriteDirectory(Action):
    """Action class for writing tutorial directories.

    Args:
        name: The name of the action.
        language: The language to output, default is "Chinese".
    """
    language: str = "Chinese"

    def __init__(self, name: str = "", language: str = "Chinese", **kwargs):
        super().__init__(**kwargs)
        self.language = language

    async def run(self, topic: str, *args, **kwargs) -> Dict:
        """Execute the action to generate a tutorial directory according to the topic.

        Args:
            topic: The tutorial topic.

        Returns:
            the tutorial directory information, including {"title": "xxx", "directory": [{"dir 1": ["sub dir 1", "sub dir 2"]}]}.
        """
        COMMON_PROMPT = """
        You are now a seasoned technical professional in the field of the internet. 
        We need you to write a technical tutorial with the topic "{topic}".
        """

        DIRECTORY_PROMPT = COMMON_PROMPT + """
        Please provide the specific table of contents for this tutorial, strictly following the following requirements:
        1. The output must be strictly in the specified language, {language}.
        2. Answer strictly in the dictionary format like {{"title": "xxx", "directory": [{{"dir 1": ["sub dir 1", "sub dir 2"]}}, {{"dir 2": ["sub dir 3", "sub dir 4"]}}]}}.
        3. The directory should be as specific and sufficient as possible, with a primary and secondary directory.The secondary directory is in the array.
        4. Do not have extra spaces or line breaks.
        5. Each directory title has practical significance.
        """
        prompt = DIRECTORY_PROMPT.format(topic=topic, language=self.language)
        resp = await self._aask(prompt=prompt)
        return OutputParser.extract_struct(resp, dict)

class WriteContent(Action):
    """Action class for writing tutorial content.

    Args:
        name: The name of the action.
        directory: The content to write.
        language: The language to output, default is "Chinese".
    """
    language: str = "Chinese"
    directory: str = ""

    def __init__(self, name: str = "", directory: str = "", language: str = "Chinese", **kwargs):
        super().__init__(**kwargs)
        self.language = language
        self.directory = directory

    async def run(self, topic: str, *args, **kwargs) -> str:
        """Execute the action to write document content according to the directory and topic.

        Args:
            topic: The tutorial topic.

        Returns:
            The written tutorial content.
        """
        COMMON_PROMPT = """
        You are now a seasoned technical professional in the field of the internet. 
        We need you to write a technical tutorial with the topic "{topic}".
        """
        CONTENT_PROMPT = COMMON_PROMPT + """
        Now I will give you the module directory titles for the topic. 
        Please output the detailed principle content of this title in detail. 
        If there are code examples, please provide them according to standard code specifications. 
        Without a code example, it is not necessary.

        The module directory titles for the topic is as follows:
        {directory}

        Strictly limit output according to the following requirements:
        1. Follow the Markdown syntax format for layout.
        2. If there are code examples, they must follow standard syntax specifications, have document annotations, and be displayed in code blocks.
        3. The output must be strictly in the specified language, {language}.
        4. Do not have redundant output, including concluding remarks.
        5. Strict requirement not to output the topic "{topic}".
        """
        prompt = CONTENT_PROMPT.format(
            topic=topic, language=self.language, directory=self.directory)
        return await self._aask(prompt=prompt)

class TutorialAssistant(Role):
    """Tutorial assistant, input one sentence to generate a tutorial document in markup format.

    Args:
        name: The name of the role.
        profile: The role profile description.
        goal: The goal of the role.
        constraints: Constraints or requirements for the role.
        language: The language in which the tutorial documents will be generated.
    """
    topic: str = ""
    main_title: str = ""
    total_content: str = ""
    language: str = ""

    def __init__(
        self,
        name: str = "Stitch",
        profile: str = "Tutorial Assistant",
        goal: str = "Generate tutorial documents",
        constraints: str = "Strictly follow Markdown's syntax, with neat and standardized layout",
        language: str = "Chinese",
    ):
        data = {
            "name": name,
            "profile": profile,
            "goal": goal,
            "constraints": constraints,
            "language": language,
        }  
        super().__init__(**data)
        self._init_actions([WriteDirectory(language=language)])
        self.topic = ""
        self.main_title = ""
        self.total_content = ""
        self.language = language

    async def _think(self) -> None:
        """Determine the next action to be taken by the role."""
        # logger.info(self.rc.state)
        # logger.info(self,)
        if self.rc.todo is None:
            self._set_state(0)
            return

        if self.rc.state + 1 < len(self.states):
            self._set_state(self.rc.state + 1)
        else:
            self.rc.todo = None

    async def _handle_directory(self, titles: Dict) -> Message:
        """Handle the directories for the tutorial document.

        Args:
            titles: A dictionary containing the titles and directory structure,
                    such as {"title": "xxx", "directory": [{"dir 1": ["sub dir 1", "sub dir 2"]}]}

        Returns:
            A message containing information about the directory.
        """
        self.main_title = titles.get("title")
        directory = f"{self.main_title}\n"
        self.total_content += f"# {self.main_title}"
        actions = list()
        for first_dir in titles.get("directory"):
            actions.append(WriteContent(
                language=self.language, directory=first_dir))
            key = list(first_dir.keys())[0]
            directory += f"- {key}\n"
            for second_dir in first_dir[key]:
                directory += f"  - {second_dir}\n"
        self._init_actions(actions)
        self.rc.todo = None
        return Message(content=directory)

    async def _act(self) -> Message:
        """Perform an action as determined by the role.

        Returns:
            A message containing the result of the action.
        """
        todo = self.rc.todo
        if type(todo) is WriteDirectory:
            msg = self.rc.memory.get(k=1)[0]
            self.topic = msg.content
            resp = await todo.run(topic=self.topic)
            # logger.info(resp)
            await self._handle_directory(resp)
            return Message(content="")
            # return await self._handle_directory(resp)
        else:
            resp = await todo.run(topic=self.topic)
            # logger.info(resp)
            if self.total_content != "":
                self.total_content += "\n\n\n"
            self.total_content += resp
            return Message(content=resp, role=self.profile)

    async def _react(self) -> Message:
        """Execute the assistant's think and actions.

        Returns:
            A message containing the final result of the assistant's actions.
        """
        while True:
            await self._think()
            if self.rc.todo is None:
                break

            msg = await self._act()
            if msg:
                yield msg.content

        # root_path = TUTORIAL_PATH / datetime.now().strftime("%Y%m%d")
        await File.write(TUTORIAL_PATH, f"{self.main_title}.md", self.total_content.encode('utf-8'))

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
        """Observe, and think and act based on the results of the observation"""
        if with_message:
            msg = Message(content=with_message)
            self.put_message(msg)

        if not await self._observe():
            # If there is no new information, suspend and wait
            logger.warning(f"{self._setting}: no news. waiting.")
            yield

        async for msg in self.react():
            async for item in msg:
                yield item

        self.rc.todo = None
        self.publish_message(self.total_content)
    
async def run(msg: str = ""):
    msg = "给我写一份mongodb教程"
    logger.info(f"input: {msg}")
    role = TutorialAssistant()
    result = role.run(msg)
    async for msg in result:
        print(f"msg:{msg}")

if __name__ == "__main__":
    result = asyncio.run(run())

