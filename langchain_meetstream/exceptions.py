"""Exceptions raised by `langchain_meetstream`.

These are framework-local -- a caller catching `MeetStreamAPIError` never
needs to know the loader/tools are backed by an HTTP call to the bridge at
all. `MeetStreamClient` (see `client.py`) is the one place that translates the
bridge's `{"error": {"code", "message"}}` JSON body into one of these.
"""

from __future__ import annotations


class MeetStreamError(Exception):
    """Base class for every exception this package raises."""


class MeetStreamAPIError(MeetStreamError):
    """The bridge server returned an error response.

    `code` is the bridge's own stable error code (e.g. `"transcript_not_ready"`,
    `"meeting_not_found"`) -- see `bridge/app/exceptions.py` for the full set --
    so callers can branch on failure type without string-matching `message`.
    """

    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class MeetStreamConnectionError(MeetStreamError):
    """Could not reach the bridge server at all (network error, timeout, or
    the bridge process isn't running) -- distinct from `MeetStreamAPIError`,
    which means the bridge *was* reached and returned an error."""
