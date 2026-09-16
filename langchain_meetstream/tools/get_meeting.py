"""The `get_meeting` tool: lets an agent look up a MeetStream meeting's status
and metadata.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from langchain_meetstream.client import MeetStreamClient


def get_meeting_tool(client: MeetStreamClient) -> BaseTool:
    """Builds the `get_meeting` tool bound to `client`."""

    @tool
    def get_meeting(meeting_id: str) -> dict:
        """Look up the current status and metadata of a MeetStream meeting.

        Use this when you need to check whether a bot has actually joined a
        meeting yet, what its current status is (e.g. still joining, in the
        meeting, or has left), or to confirm a `meeting_id` is valid before
        calling `get_meeting_transcript` or a meeting-action tool.

        Args:
            meeting_id: The meeting id returned by `dispatch_meetstream_bot`.

        Returns:
            A dict with `meeting_id`, `status`, and (when known) `platform`,
            `meeting_url`, `title`, `started_at`, `ended_at`, and
            `custom_attributes`. Several of these are commonly `None` --
            MeetStream's status endpoint does not expose a meeting title or
            join/leave timestamps; see this package's README "Known
            limitations" section.

        Raises:
            langchain_meetstream.MeetStreamAPIError: `code="meeting_not_found"`
                if no such meeting exists.
        """
        result = client.get_meeting(meeting_id)
        return result.model_dump()

    return get_meeting
