"""Tools for the confirmed-real MeetStream active-meeting actions.

Three separate, typed tools (rather than one `perform_meeting_action(action:
str, **kwargs)` tool) -- per this project's design guidance, when several
substantially different actions exist it's clearer for both the LLM and the
developer to expose separate, precisely-typed tool functions than one vague,
dict-payload "do an action" tool. Each of these maps 1:1 to a MeetStream
capability confirmed real by a reference implementation -- see
`docs/ARCHITECTURE.md` §3 and `bridge/app/services/bot_service.py`.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from langchain_meetstream.client import MeetStreamClient


def get_send_chat_message_tool(client: MeetStreamClient) -> BaseTool:
    """Builds the `send_meeting_chat_message` tool bound to `client`."""

    @tool
    def send_meeting_chat_message(meeting_id: str, message: str) -> dict:
        """Post a text message into a live MeetStream meeting's chat.

        Use this when a user asks you to tell participants something during
        a meeting, e.g. "let everyone know the deadline moved to Friday."
        Only works while the bot is actively in the meeting.

        Args:
            meeting_id: The meeting id returned by `dispatch_meetstream_bot`.
            message: The chat message text to send.

        Returns:
            A dict with `meeting_id`, `action`, `status`, and `detail`.

        Raises:
            langchain_meetstream.MeetStreamAPIError: `code="meeting_not_found"`
                if the bot is no longer in that meeting.
        """
        return client.send_chat_message(meeting_id, message).model_dump()

    return send_meeting_chat_message


def get_send_image_tool(client: MeetStreamClient) -> BaseTool:
    """Builds the `send_meeting_image` tool bound to `client`."""

    @tool
    def send_meeting_image(meeting_id: str, image_url: str, display_duration_seconds: float | None = None) -> dict:
        """Display an image as the bot's video feed in a live MeetStream meeting.

        Use this when a user asks you to show a slide, chart, or picture in a
        meeting. `image_url` must already be a publicly reachable URL --
        MeetStream does not accept inline/base64 image data on this action.

        Args:
            meeting_id: The meeting id returned by `dispatch_meetstream_bot`.
            image_url: A publicly reachable URL of the image to display.
            display_duration_seconds: How long to display the image, in
                seconds. Omit to use MeetStream's default duration.

        Returns:
            A dict with `meeting_id`, `action`, `status`, and `detail`.

        Raises:
            langchain_meetstream.MeetStreamAPIError: `code="meeting_not_found"`
                if the bot is no longer in that meeting.
        """
        return client.send_image(meeting_id, image_url, display_duration_seconds).model_dump()

    return send_meeting_image


def get_leave_meeting_tool(client: MeetStreamClient) -> BaseTool:
    """Builds the `leave_meeting` tool bound to `client`."""

    @tool
    def leave_meeting(meeting_id: str) -> dict:
        """Make the MeetStream bot leave a live meeting.

        Use this when a user asks you to remove the bot from a meeting, or a
        meeting has ended and the bot should stop recording. Already-recorded
        data (transcript, etc.) is preserved and remains retrievable via
        `get_meeting_transcript` after the bot leaves.

        Args:
            meeting_id: The meeting id returned by `dispatch_meetstream_bot`.

        Returns:
            A dict with `meeting_id`, `action`, `status`, and `detail`.

        Raises:
            langchain_meetstream.MeetStreamAPIError: `code="meeting_not_found"`
                if the bot has already left or never existed.
        """
        return client.leave_meeting(meeting_id).model_dump()

    return leave_meeting
