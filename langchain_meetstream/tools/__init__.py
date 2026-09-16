"""LangChain-native tools for interacting with MeetStream from an agent.

`get_meetstream_tools(client)` is the primary, ergonomic entry point:

    ```python
    from langchain_meetstream import MeetStreamClient
    from langchain_meetstream.tools import get_meetstream_tools

    client = MeetStreamClient(api_key="...")
    tools = get_meetstream_tools(client)
    ```

These are plain `BaseTool` objects -- they work with any LangChain
tool-calling agent (`langchain.agents.create_agent`, a raw
`model.bind_tools(tools)`, etc.). There is no separate "MeetStream agent"
class; the point of this module is to give *existing* agents MeetStream
capabilities, not to build a new agent abstraction.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool

from langchain_meetstream.client import MeetStreamClient
from langchain_meetstream.tools.dispatch_bot import get_dispatch_bot_tool
from langchain_meetstream.tools.get_meeting import get_meeting_tool
from langchain_meetstream.tools.get_transcript import get_transcript_tool
from langchain_meetstream.tools.meeting_action import (
    get_leave_meeting_tool,
    get_send_chat_message_tool,
    get_send_image_tool,
)


def get_meetstream_tools(client: MeetStreamClient) -> list[BaseTool]:
    """Returns every MeetStream tool, bound to `client`.

    Covers all four capability areas this integration supports: dispatching a
    bot, retrieving meeting metadata, retrieving a transcript, and performing
    the confirmed-real active-meeting actions (chat message, image, leave).
    """
    return [
        get_dispatch_bot_tool(client),
        get_meeting_tool(client),
        get_transcript_tool(client),
        get_send_chat_message_tool(client),
        get_send_image_tool(client),
        get_leave_meeting_tool(client),
    ]


__all__ = [
    "get_dispatch_bot_tool",
    "get_leave_meeting_tool",
    "get_meeting_tool",
    "get_meetstream_tools",
    "get_send_chat_message_tool",
    "get_send_image_tool",
    "get_transcript_tool",
]
