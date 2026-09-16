"""`MeetStreamClient` -- the shared HTTP client this package uses to talk to
the MeetStream **bridge** (never to MeetStream's own API directly; see
`docs/ARCHITECTURE.md` in the repo root).

Layer: this is the one module in `langchain_meetstream` that knows the
bridge's HTTP contract (paths, request/response JSON shapes). Both
`document_loaders/meetstream.py` and every module under `tools/` import this
client rather than making their own HTTP calls -- see
`docs/ARCHITECTURE.md` §8 for why a shared client is the right call in this
bridge-backed design (an earlier, pre-bridge prototype at this same
repository path had explicitly rejected a shared client; that guidance no
longer applies once the packages stopped talking to MeetStream directly).
"""

from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from langchain_meetstream.exceptions import MeetStreamAPIError, MeetStreamConnectionError


class MeetingMetadata(BaseModel):
    """Mirrors the bridge's `MeetingMetadata` response. See
    `docs/ARCHITECTURE.md` §6 for why `title`/`started_at`/`ended_at` are
    routinely `None` -- that's not a bug in this client."""

    meeting_id: str
    status: str
    platform: str | None = None
    meeting_url: str | None = None
    title: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    custom_attributes: dict[str, Any] | None = None


class TranscriptSegment(BaseModel):
    text: str
    speaker: str | None = None
    start_time: float | None = None
    end_time: float | None = None


class Transcript(BaseModel):
    meeting_id: str
    segments: list[TranscriptSegment]


class BotDispatchResult(BaseModel):
    bot_id: str
    meeting_id: str
    status: str


class MeetingActionResult(BaseModel):
    meeting_id: str
    action: str
    status: str
    detail: str | None = None


class MeetStreamClient:
    """Synchronous HTTP client for the MeetStream bridge.

    Example:
        ```python
        from langchain_meetstream import MeetStreamClient

        client = MeetStreamClient(api_key="...", base_url="http://localhost:8000")
        meeting = client.get_meeting("meeting_123")
        ```

    Synchronous rather than async: this is what `MeetStreamLoader.lazy_load()`
    and the `@tool`-decorated functions in `tools/` need, and it's the
    overwhelmingly common case for a script or notebook calling
    `loader.load()` with no event loop already running -- see
    `docs/ARCHITECTURE.md` §11 for the full reasoning, including why this
    doesn't block async LangChain callers (`BaseLoader.aload()` wraps this in
    a thread executor for free).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        # Falls back to environment variables so `MeetStreamClient()` works
        # unconfigured in a shell that already exports these -- matching the
        # ergonomics of most provider SDKs (OpenAI, Anthropic, etc.) that
        # LangChain users are already used to.
        resolved_api_key = api_key or os.environ.get("MEETSTREAM_API_KEY")
        if not resolved_api_key:
            raise ValueError(
                "MeetStream API key is required. Pass api_key=... or set the MEETSTREAM_API_KEY environment variable."
            )
        resolved_base_url = base_url or os.environ.get("MEETSTREAM_BRIDGE_URL") or "http://localhost:8000"

        # One connection-pooled httpx.Client per MeetStreamClient instance
        # (not one per call) -- same rationale as bridge/app/clients/meetstream.py.
        # This client authenticates to the BRIDGE, not to MeetStream itself;
        # the bridge is the only thing that ever sees the real MeetStream API key.
        self._http = httpx.Client(
            base_url=resolved_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {resolved_api_key}"},
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> MeetStreamClient:  # noqa: PYI034 -- `Self` needs 3.11+; this package supports 3.10.
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _request(self, method: str, path: str, *, json: dict[str, Any] | None = None) -> Any:
        try:
            response = self._http.request(method, path, json=json)
        except httpx.RequestError as exc:
            raise MeetStreamConnectionError(f"Could not reach MeetStream bridge at {self._http.base_url}: {exc}") from exc

        if response.status_code >= 400:
            code = "unknown_error"
            message = f"Bridge request failed with status {response.status_code}"
            try:
                body = response.json()
                error = body.get("error", {})
                code = error.get("code", code)
                message = error.get("message", message)
            except ValueError:
                pass
            raise MeetStreamAPIError(message, code=code, status_code=response.status_code)

        return response.json() if response.content else None

    def dispatch_bot(self, meeting_url: str, bot_name: str = "MeetStream Bot") -> BotDispatchResult:
        """Sends a MeetStream bot into a meeting. See `POST /bots` on the bridge."""
        raw = self._request("POST", "/bots", json={"meeting_url": meeting_url, "bot_name": bot_name})
        return BotDispatchResult.model_validate(raw)

    def get_meeting(self, meeting_id: str) -> MeetingMetadata:
        """Retrieves normalized meeting metadata. See `GET /meetings/{meeting_id}`."""
        raw = self._request("GET", f"/meetings/{meeting_id}")
        return MeetingMetadata.model_validate(raw)

    def get_transcript(self, meeting_id: str) -> Transcript:
        """Retrieves the normalized transcript. See `GET /meetings/{meeting_id}/transcript`.

        Raises `MeetStreamAPIError` with `code="transcript_not_ready"` if
        MeetStream hasn't finished processing it yet, or
        `code="transcript_unavailable"` if it never will.
        """
        raw = self._request("GET", f"/meetings/{meeting_id}/transcript")
        return Transcript.model_validate(raw)

    def send_chat_message(self, meeting_id: str, message: str) -> MeetingActionResult:
        """Posts `message` into the meeting's chat."""
        raw = self._request(
            "POST", f"/meetings/{meeting_id}/actions", json={"action": "send_chat_message", "payload": {"message": message}}
        )
        return MeetingActionResult.model_validate(raw)

    def send_image(self, meeting_id: str, image_url: str, display_duration_seconds: float | None = None) -> MeetingActionResult:
        """Sets the bot's video feed to `image_url` (must be publicly reachable)."""
        payload: dict[str, Any] = {"image_url": image_url}
        if display_duration_seconds is not None:
            payload["display_duration_seconds"] = display_duration_seconds
        raw = self._request("POST", f"/meetings/{meeting_id}/actions", json={"action": "send_image", "payload": payload})
        return MeetingActionResult.model_validate(raw)

    def leave_meeting(self, meeting_id: str) -> MeetingActionResult:
        """Makes the bot leave the meeting. Recorded data is preserved."""
        raw = self._request("POST", f"/meetings/{meeting_id}/actions", json={"action": "leave_meeting"})
        return MeetingActionResult.model_validate(raw)

    def perform_meeting_action(
        self, meeting_id: str, action: Literal["send_chat_message", "send_image", "leave_meeting"], **payload: Any
    ) -> MeetingActionResult:
        """Generic entry point for any supported meeting action, dispatching
        by `action` name. `dispatch_bot`/`send_chat_message`/`send_image`/
        `leave_meeting` above are the preferred, typed way to call these; this
        exists for callers (like `tools/meeting_action.py`) that already have
        `action` as a runtime string, e.g. from an LLM's tool call."""
        raw = self._request("POST", f"/meetings/{meeting_id}/actions", json={"action": action, "payload": payload or None})
        return MeetingActionResult.model_validate(raw)
