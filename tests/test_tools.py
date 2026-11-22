"""Tests for `langchain_meetstream.tools`."""

from __future__ import annotations

import json

import httpx
import pytest

from langchain_meetstream.exceptions import MeetStreamAPIError
from langchain_meetstream.tools import get_meetstream_tools


def _tool(name: str, client):
    return {t.name: t for t in get_meetstream_tools(client)}[name]


def test_get_meetstream_tools_returns_six_tools(client):
    assert {t.name for t in get_meetstream_tools(client)} == {
        "dispatch_meetstream_bot",
        "get_meeting",
        "get_meeting_transcript",
        "send_meeting_chat_message",
        "send_meeting_image",
        "leave_meeting",
    }


def test_dispatch_tool_parameters(api_mock, client):
    api_mock.post("/bots/create_bot").mock(
        return_value=httpx.Response(201, json={"bot_id": "bot_1", "transcript_id": "tr_1", "status": "Active"})
    )
    result = _tool("dispatch_meetstream_bot", client).invoke(
        {"meeting_url": "https://meet.google.com/abc-defg-hij", "bot_name": "Standup Bot"}
    )

    assert result == {"bot_id": "bot_1", "meeting_id": "bot_1", "status": "Active", "transcript_id": "tr_1"}
    sent = json.loads(api_mock.calls.last.request.content)
    assert sent["bot_name"] == "Standup Bot"
    assert sent["recording_config"]["transcript"]["provider"] == {"meetstream": {"language": "auto"}}


def test_dispatch_tool_never_exposes_provider_to_the_model(client):
    assert set(_tool("dispatch_meetstream_bot", client).args) == {"meeting_url", "bot_name"}


def test_get_meeting_tool(api_mock, client):
    api_mock.get("/bots/bot_1/status").mock(return_value=httpx.Response(200, json={"bot_id": "bot_1", "status": "InMeeting"}))
    result = _tool("get_meeting", client).invoke({"meeting_id": "bot_1"})
    assert result["status"] == "InMeeting"


def test_transcript_tool(api_mock, client):
    api_mock.get("/bots/bot_1/get_transcript").mock(return_value=httpx.Response(200, json=[{"transcript": "Hi"}]))
    result = _tool("get_meeting_transcript", client).invoke({"meeting_id": "bot_1"})
    assert result["segments"][0]["text"] == "Hi"


def test_meeting_action_tool_send_chat_message(api_mock, client):
    api_mock.post("/bots/bot_1/send_message").mock(return_value=httpx.Response(200, json={"status": "accepted"}))
    result = _tool("send_meeting_chat_message", client).invoke({"meeting_id": "bot_1", "message": "hello everyone"})
    assert result["detail"] == "accepted"


def test_meeting_action_tool_leave_meeting(api_mock, client):
    api_mock.get("/bots/bot_1/remove_bot").mock(return_value=httpx.Response(200, json={"status": "stopped"}))
    result = _tool("leave_meeting", client).invoke({"meeting_id": "bot_1"})
    assert result["detail"] == "stopped"


def test_tool_error_propagation(api_mock, client):
    api_mock.get("/bots/missing/get_transcript").mock(return_value=httpx.Response(404, json={"message": "Bot not found"}))
    with pytest.raises(MeetStreamAPIError) as excinfo:
        _tool("get_meeting_transcript", client).invoke({"meeting_id": "missing"})
    assert excinfo.value.code == "meeting_not_found"


def test_each_tool_has_a_nonempty_description(client):
    for tool in get_meetstream_tools(client):
        assert tool.description and len(tool.description) > 20
