"""The `dispatch_meetstream_bot` tool: lets an agent send a MeetStream bot
into a meeting.

Layer: framework adapter. Wraps `MeetStreamClient.dispatch_bot` (which itself
just calls the bridge's `POST /bots`) as a LangChain `BaseTool`. Contains no
MeetStream-specific logic -- only the LangChain-facing description and return
shape.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from langchain_meetstream.client import MeetStreamClient


def get_dispatch_bot_tool(client: MeetStreamClient) -> BaseTool:
    """Builds the `dispatch_meetstream_bot` tool bound to `client`.

    A factory function (rather than a module-level `@tool`-decorated
    function) because the tool needs a `MeetStreamClient` closed over it --
    `@tool` infers the LLM-visible argument schema from the wrapped
    function's signature, so `client` cannot itself be a parameter the model
    would see and try to fill in.
    """

    @tool
    def dispatch_meetstream_bot(meeting_url: str, bot_name: str = "MeetStream Bot") -> dict:
        """Send a MeetStream bot to join a live meeting.

        Use this when a user asks you to record, transcribe, or otherwise
        have a bot join a meeting that is happening now or about to start
        (Google Meet, Zoom, or Microsoft Teams). Returns the new bot's id
        (also usable as `meeting_id` for `get_meeting`/`get_meeting_transcript`/
        meeting-action tools) and its initial join status -- dispatching is
        asynchronous, so the returned status is an early one (e.g. "Active"),
        not yet "in the meeting"; call `get_meeting` afterward if you need to
        confirm the bot has actually joined.

        Args:
            meeting_url: The full URL of the meeting to join.
            bot_name: The display name the bot should use inside the meeting.

        Returns:
            A dict with `bot_id`, `meeting_id` (identical to `bot_id`), and `status`.

        Raises:
            langchain_meetstream.MeetStreamAPIError: e.g. `code="invalid_meeting_url"`
                if MeetStream rejects the URL, or `code="authentication_failed"`.
        """
        result = client.dispatch_bot(meeting_url=meeting_url, bot_name=bot_name)
        return result.model_dump()

    return dispatch_meetstream_bot
