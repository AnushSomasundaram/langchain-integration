#!/usr/bin/env python3
"""LangChain package smoke test -- MOCKED bridge responses only (no real
bridge or MeetStream call). For a real-data version of this same check, see
`live_langchain_test.py`, which requires a real `--bot-id`.

Everything below imports the ACTUAL project code
(`langchain_meetstream.MeetStreamClient`/`MeetStreamLoader`/
`get_meetstream_tools`) -- this script does not reimplement any parsing or
tool logic, it only feeds those real objects a mocked bridge HTTP response
(via `respx`, the same library `tests/` already uses) and inspects what
comes back.

Standalone usage:
    python scripts/verification/check_langchain.py

Importable:
    from check_langchain import run
    results = run()
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib

_MOCK_BRIDGE_URL = "http://verification-mock-bridge"


def check_imports() -> _lib.CheckResult:
    try:
        from langchain_meetstream import (  # noqa: F401
            MeetStreamAPIError,
            MeetStreamClient,
            MeetStreamConnectionError,
            MeetStreamLoader,
        )
        from langchain_meetstream.tools import get_meetstream_tools  # noqa: F401
    except ImportError as exc:
        return _lib.CheckResult(
            "LangChain package imports",
            _lib.STATUS_FAIL,
            error=str(exc),
            hint=f"pip install -e '{_lib.LANGCHAIN_DIR}[dev]'",
        )
    return _lib.CheckResult("LangChain package imports", _lib.STATUS_PASS)


def check_client_construction() -> _lib.CheckResult:
    try:
        from langchain_meetstream import MeetStreamClient

        client = MeetStreamClient(api_key="verification-mock-key", base_url=_MOCK_BRIDGE_URL)
        client.close()
    except Exception as exc:  # noqa: BLE001 -- catches any failure from the real project code under test, not just anticipated ones
        return _lib.CheckResult("LangChain client construction", _lib.STATUS_FAIL, error=str(exc))
    return _lib.CheckResult("LangChain client construction", _lib.STATUS_PASS)


def check_loader() -> list[_lib.CheckResult]:
    """Feeds MeetStreamLoader a mocked bridge response with a deliberately
    incomplete meeting (no title, one segment missing a speaker) and asserts
    the REAL loader code neither crashes nor fabricates the missing fields --
    this is the single most important thing this project promises (see
    docs/ARCHITECTURE.md §6): a None field must stay None, never invented.
    """
    import httpx
    import respx

    from langchain_meetstream import MeetStreamClient
    from langchain_meetstream.document_loaders import MeetStreamLoader

    results = []
    try:
        with respx.mock(base_url=_MOCK_BRIDGE_URL, assert_all_called=False) as router:
            router.get("/meetings/verify-meeting-1/transcript").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "meeting_id": "verify-meeting-1",
                        "segments": [
                            {"text": "The launch date is October 14.", "speaker": "Sarah", "start_time": 1.0, "end_time": 4.5},
                            {"text": "Understood, thanks."},  # deliberately missing speaker/timestamps
                        ],
                    },
                )
            )
            router.get("/meetings/verify-meeting-1").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "meeting_id": "verify-meeting-1",
                        "status": "completed",
                        "platform": None,
                        "meeting_url": None,
                        "title": None,
                        "started_at": None,
                        "ended_at": None,
                        "custom_attributes": None,
                    },
                )
            )
            client = MeetStreamClient(api_key="verification-mock-key", base_url=_MOCK_BRIDGE_URL)
            docs = MeetStreamLoader(meeting_id="verify-meeting-1", client=client).load()
    except Exception as exc:  # noqa: BLE001 -- catches any failure from the real project code under test, not just anticipated ones
        return [_lib.CheckResult("LangChain loader (mocked)", _lib.STATUS_FAIL, error=str(exc))]

    from langchain_core.documents import Document

    if len(docs) != 2 or not all(isinstance(d, Document) for d in docs):
        return [_lib.CheckResult("LangChain loader returns Documents", _lib.STATUS_FAIL, error=f"expected 2 langchain_core Document objects, got {docs!r}")]
    results.append(_lib.CheckResult("LangChain loader returns Documents", _lib.STATUS_PASS, detail=f"({len(docs)} Documents)"))

    if docs[0].page_content != "The launch date is October 14.":
        results.append(_lib.CheckResult("LangChain loader page_content", _lib.STATUS_FAIL, error=f"unexpected page_content: {docs[0].page_content!r}"))
    else:
        results.append(_lib.CheckResult("LangChain loader page_content", _lib.STATUS_PASS))

    md = docs[0].metadata
    expected_keys = {"source", "meeting_id", "meeting_title", "platform", "speaker", "start_time", "end_time"}
    if set(md) != expected_keys or md["speaker"] != "Sarah" or md["start_time"] != 1.0:
        results.append(_lib.CheckResult("LangChain loader metadata", _lib.STATUS_FAIL, error=f"unexpected metadata: {md}"))
    else:
        results.append(_lib.CheckResult("LangChain loader metadata", _lib.STATUS_PASS))

    md2 = docs[1].metadata
    no_fabrication_ok = md2["speaker"] is None and md2["start_time"] is None and md2["end_time"] is None and md2["meeting_title"] is None
    if not no_fabrication_ok:
        results.append(
            _lib.CheckResult(
                "LangChain loader does not fabricate missing fields",
                _lib.STATUS_FAIL,
                error=f"expected speaker/start_time/end_time/meeting_title to be None for an incomplete segment, got: {md2}",
            )
        )
    else:
        results.append(_lib.CheckResult("LangChain loader does not fabricate missing fields", _lib.STATUS_PASS))

    return results


def check_tools(verbose: bool = True) -> list[_lib.CheckResult]:
    from langchain_meetstream import MeetStreamClient
    from langchain_meetstream.tools import get_meetstream_tools

    # The real capabilities this bridge exposes (see bridge/app/models/bot.py
    # `MeetingActionType` and bridge/app/api/*.py) -- used below only to
    # assert the tool set matches what MeetStream/the bridge actually
    # supports, never to invent a tool.
    expected_tool_names = {
        "dispatch_meetstream_bot",
        "get_meeting",
        "get_meeting_transcript",
        "send_meeting_chat_message",
        "send_meeting_image",
        "leave_meeting",
    }

    client = MeetStreamClient(api_key="verification-mock-key", base_url=_MOCK_BRIDGE_URL)
    tools = get_meetstream_tools(client)
    results = []

    actual_names = {t.name for t in tools}
    if actual_names != expected_tool_names:
        results.append(
            _lib.CheckResult(
                "LangChain tools discovered",
                _lib.STATUS_FAIL,
                error=f"expected {sorted(expected_tool_names)}, got {sorted(actual_names)}",
            )
        )
    else:
        results.append(_lib.CheckResult("LangChain tools discovered", _lib.STATUS_PASS, detail=f"({len(tools)} tools)"))

    if verbose:
        print()
        for i, tool in enumerate(tools, start=1):
            print(f"Tool {i}: {tool.name}")
            print(f"Description: {tool.description.splitlines()[0] if tool.description else '(none)'}")
        print()

    for tool in tools:
        label = f"  {tool.name}"
        problems = []
        if not tool.name:
            problems.append("empty name")
        if not tool.description or len(tool.description.strip()) < 20:
            problems.append("description missing or too short to be useful")
        schema = getattr(tool, "args_schema", None)
        if schema is None:
            problems.append("no args_schema (input schema)")
        if problems:
            results.append(_lib.CheckResult(f"{label} well-formed", _lib.STATUS_FAIL, error="; ".join(problems)))
        else:
            results.append(_lib.CheckResult(f"{label} well-formed", _lib.STATUS_PASS))

    return results


def check_tool_invocation() -> list[_lib.CheckResult]:
    """Invokes each tool through a mocked bridge to confirm the tool
    actually calls the bridge with the right method/path and returns the
    bridge's (mocked) response -- not just that the tool object exists."""
    import httpx
    import respx

    from langchain_meetstream import MeetStreamClient
    from langchain_meetstream.tools import get_meetstream_tools

    results = []
    with respx.mock(base_url=_MOCK_BRIDGE_URL, assert_all_called=False) as router:
        router.post("/bots").mock(return_value=httpx.Response(200, json={"bot_id": "b1", "meeting_id": "b1", "status": "Active"}))
        router.get("/meetings/b1").mock(return_value=httpx.Response(200, json={"meeting_id": "b1", "status": "InMeeting"}))
        router.get("/meetings/b1/transcript").mock(return_value=httpx.Response(200, json={"meeting_id": "b1", "segments": []}))
        router.post("/meetings/b1/actions").mock(
            return_value=httpx.Response(200, json={"meeting_id": "b1", "action": "send_chat_message", "status": "ok", "detail": "sent"})
        )

        client = MeetStreamClient(api_key="verification-mock-key", base_url=_MOCK_BRIDGE_URL)
        tools = {t.name: t for t in get_meetstream_tools(client)}

        invocations = [
            ("dispatch_meetstream_bot", {"meeting_url": "https://meet.google.com/verify-abc", "bot_name": "Verify Bot"}),
            ("get_meeting", {"meeting_id": "b1"}),
            ("get_meeting_transcript", {"meeting_id": "b1"}),
            ("send_meeting_chat_message", {"meeting_id": "b1", "message": "verification message"}),
        ]
        for name, kwargs in invocations:
            try:
                output = tools[name].invoke(kwargs)
                results.append(_lib.CheckResult(f"  invoke {name}", _lib.STATUS_PASS, detail=f"-> {output}"[:100]))
            except Exception as exc:  # noqa: BLE001 -- catches any failure from the real project code under test, not just anticipated ones
                results.append(_lib.CheckResult(f"  invoke {name}", _lib.STATUS_FAIL, error=str(exc)))
    return results


def run(verbose: bool = True) -> list[_lib.CheckResult]:
    results = [check_imports()]
    if results[0].status == _lib.STATUS_FAIL:
        return results  # nothing else below can run without the import
    results.append(check_client_construction())
    results.extend(check_loader())
    results.extend(check_tools(verbose=verbose))
    results.extend(check_tool_invocation())
    return results


def main() -> int:
    _lib.print_section("LangChain package verification (mocked bridge)")
    results = run(verbose=True)
    for r in results:
        _lib.print_result(r)
    return 0 if all(r.status != _lib.STATUS_FAIL for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
