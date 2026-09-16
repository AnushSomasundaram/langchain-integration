"""Tests for `langchain_meetstream.tools`."""

from __future__ import annotations

import httpx
import pytest

from langchain_meetstream.client import MeetStreamClient
from langchain_meetstream.exceptions import MeetStreamAPIError
from langchain_meetstream.tools import get_meetstream_tools

BRIDGE_URL = "http://test-bridge"


def _client() -> MeetStreamClient:
    return MeetStreamClient(api_key="k", base_url=BRIDGE_URL)


def _tool(name: str, client: MeetStreamClient):
    tools = {t.name: t for t in get_meetstream_tools(client)}
    return tools[name]


def test_get_meetstream_tools_returns_six_tools():
    tools = get_meetstream_tools(_client())
    names = {t.name for t in tools}
    assert names == {
        "dispatch_meetstream_bot",
        "get_meeting",
        "get_meeting_transcript",
        "send_meeting_chat_message",
        "send_meeting_image",
        "leave_meeting",
    }


def test_dispatch_tool_parameters(bridge_mock):
    bridge_mock.post("/bots").mock(
        return_value=httpx.Response(200, json={"bot_id": "bot_1", "meeting_id": "bot_1", "status": "joining"})
    )
    client = _client()
    tool = _tool("dispatch_meetstream_bot", client)

    result = tool.invoke({"meeting_url": "https://meet.google.com/abc-defg-hij", "bot_name": "Standup Bot"})

    assert result == {"bot_id": "bot_1", "meeting_id": "bot_1", "status": "joining"}
    sent_body = bridge_mock.calls.last.request.content
    assert b"Standup Bot" in sent_body


def test_get_meeting_tool(bridge_mock):
    bridge_mock.get("/meetings/bot_1").mock(
        return_value=httpx.Response(200, json={"meeting_id": "bot_1", "status": "InMeeting", "platform": "zoom"})
    )
    client = _client()
    tool = _tool("get_meeting", client)

    result = tool.invoke({"meeting_id": "bot_1"})

    assert result["status"] == "InMeeting"
    assert result["platform"] == "zoom"


def test_transcript_tool(bridge_mock):
    bridge_mock.get("/meetings/bot_1/transcript").mock(
        return_value=httpx.Response(200, json={"meeting_id": "bot_1", "segments": [{"text": "Hi", "speaker": None, "start_time": None, "end_time": None}]})
    )
    client = _client()
    tool = _tool("get_meeting_transcript", client)

    result = tool.invoke({"meeting_id": "bot_1"})

    assert result["segments"][0]["text"] == "Hi"


def test_meeting_action_tool_send_chat_message(bridge_mock):
    bridge_mock.post("/meetings/bot_1/actions").mock(
        return_value=httpx.Response(200, json={"meeting_id": "bot_1", "action": "send_chat_message", "status": "ok", "detail": "sent"})
    )
    client = _client()
    tool = _tool("send_meeting_chat_message", client)

    result = tool.invoke({"meeting_id": "bot_1", "message": "hello everyone"})

    assert result["detail"] == "sent"


def test_meeting_action_tool_leave_meeting(bridge_mock):
    bridge_mock.post("/meetings/bot_1/actions").mock(
        return_value=httpx.Response(200, json={"meeting_id": "bot_1", "action": "leave_meeting", "status": "ok", "detail": "removed"})
    )
    client = _client()
    tool = _tool("leave_meeting", client)

    result = tool.invoke({"meeting_id": "bot_1"})

    assert result["detail"] == "removed"


def test_tool_error_propagation(bridge_mock):
    bridge_mock.get("/meetings/missing/transcript").mock(
        return_value=httpx.Response(404, json={"error": {"code": "meeting_not_found", "message": "no such meeting"}})
    )
    client = _client()
    tool = _tool("get_meeting_transcript", client)

    with pytest.raises(MeetStreamAPIError) as excinfo:
        tool.invoke({"meeting_id": "missing"})
    assert excinfo.value.code == "meeting_not_found"


def test_each_tool_has_a_nonempty_description():
    tools = get_meetstream_tools(_client())
    for tool in tools:
        assert tool.description and len(tool.description) > 20
