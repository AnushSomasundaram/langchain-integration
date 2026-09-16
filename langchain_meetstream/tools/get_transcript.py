"""The `get_meeting_transcript` tool: lets an agent read what was said in a
MeetStream meeting.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from langchain_meetstream.client import MeetStreamClient


def get_transcript_tool(client: MeetStreamClient) -> BaseTool:
    """Builds the `get_meeting_transcript` tool bound to `client`."""

    @tool
    def get_meeting_transcript(meeting_id: str) -> dict:
        """Retrieve the transcript for a MeetStream meeting using its meeting ID.

        Use this when you need to inspect, summarize, search, or reason about
        what participants said during a meeting -- for example "what did
        Sarah say about the deadline?" or "summarize this meeting."

        Args:
            meeting_id: The meeting id returned by `dispatch_meetstream_bot`.

        Returns:
            A dict with `meeting_id` and `segments`: a list of
            `{"text", "speaker", "start_time", "end_time"}` objects, one per
            speaker turn, in chronological order. `segments` is an empty list
            for a real meeting that captured no speech -- not an error.

        Raises:
            langchain_meetstream.MeetStreamAPIError: `code="transcript_not_ready"`
                if MeetStream is still processing the transcript (retry later),
                `code="transcript_unavailable"` if one will never exist, or
                `code="meeting_not_found"` if `meeting_id` is invalid.
        """
        result = client.get_transcript(meeting_id)
        return result.model_dump()

    return get_meeting_transcript
