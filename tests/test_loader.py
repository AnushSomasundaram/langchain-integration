"""Tests for `langchain_meetstream.document_loaders.MeetStreamLoader`."""

from __future__ import annotations

import httpx
import pytest
from langchain_core.documents import Document

from langchain_meetstream.document_loaders import MeetStreamLoader
from langchain_meetstream.exceptions import MeetStreamAPIError

from .conftest import API_URL


def _mock_transcript(api_mock, body, meeting_id: str = "bot_1", status: int = 200):
    api_mock.get(f"/bots/{meeting_id}/get_transcript").mock(return_value=httpx.Response(status, json=body))


def _mock_status(api_mock, meeting_id: str = "bot_1"):
    api_mock.get(f"/bots/{meeting_id}/status").mock(
        return_value=httpx.Response(200, json={"bot_id": meeting_id, "status": "Stopped", "custom_attributes": {}})
    )


def test_loader_returns_one_document_per_segment(api_mock, client):
    _mock_transcript(api_mock, [
        {"speaker": "Alex", "transcript": "Engineering should finish this Friday.", "start_time": 14.2, "end_time": 18.6},
        {"speaker": "Priya", "transcript": "Sounds good.", "start_time": 19.0, "end_time": 20.1},
    ])
    _mock_status(api_mock)

    docs = MeetStreamLoader(meeting_id="bot_1", client=client).load()

    assert len(docs) == 2
    assert all(isinstance(d, Document) for d in docs)
    assert docs[0].page_content == "Engineering should finish this Friday."


def test_loader_metadata_is_correct(api_mock, client):
    api_mock.post("/bots/create_bot").mock(
        return_value=httpx.Response(201, json={"bot_id": "bot_1", "meeting_url": "https://meet.google.com/abc-defg-hij", "status": "Active"})
    )
    client.dispatch_bot("https://meet.google.com/abc-defg-hij")
    _mock_transcript(api_mock, [{"speaker": "Alex", "transcript": "Hello.", "start_time": 1.0, "end_time": 2.0}])
    _mock_status(api_mock)

    [doc] = MeetStreamLoader(meeting_id="bot_1", client=client).load()

    assert doc.metadata == {
        "source": "meetstream",
        "meeting_id": "bot_1",
        "meeting_title": None,
        "platform": "google_meet",
        "speaker": "Alex",
        "start_time": 1.0,
        "end_time": 2.0,
    }


def test_loader_handles_empty_transcript(api_mock, client):
    _mock_transcript(api_mock, [])
    _mock_status(api_mock)
    assert MeetStreamLoader(meeting_id="bot_1", client=client).load() == []


def test_loader_handles_missing_speaker_and_timestamps(api_mock, client):
    _mock_transcript(api_mock, [{"transcript": "Anonymous remark."}])
    _mock_status(api_mock)

    [doc] = MeetStreamLoader(meeting_id="bot_1", client=client).load()

    assert doc.metadata["speaker"] is None
    assert doc.metadata["start_time"] is None
    assert doc.metadata["end_time"] is None


def test_loader_metadata_fetch_failure_does_not_fail_the_load(api_mock, client):
    _mock_transcript(api_mock, [{"transcript": "Hello."}])
    api_mock.get("/bots/bot_1/status").mock(return_value=httpx.Response(404, json={"message": "not found"}))

    docs = MeetStreamLoader(meeting_id="bot_1", client=client).load()

    assert len(docs) == 1
    assert docs[0].metadata["platform"] is None


def test_loader_transcript_not_ready_raises(api_mock, client):
    _mock_transcript(api_mock, {"message": "Still processing"}, status=202)
    with pytest.raises(MeetStreamAPIError) as excinfo:
        MeetStreamLoader(meeting_id="bot_1", client=client).load()
    assert excinfo.value.code == "transcript_not_ready"


def test_loader_invalid_meeting_raises(api_mock, client):
    _mock_transcript(api_mock, {"message": "Bot not found"}, meeting_id="does-not-exist", status=404)
    with pytest.raises(MeetStreamAPIError) as excinfo:
        MeetStreamLoader(meeting_id="does-not-exist", client=client).load()
    assert excinfo.value.code == "meeting_not_found"


def test_loader_constructs_own_client_from_api_key(api_mock):
    _mock_transcript(api_mock, [])
    _mock_status(api_mock)
    assert MeetStreamLoader(meeting_id="bot_1", api_key="k", base_url=API_URL).load() == []
    assert api_mock.calls[0].request.headers["Authorization"] == "Token k"
