"""`MeetStreamLoader` -- turns a MeetStream meeting transcript into LangChain
`Document` objects.

Layer: this is where `langchain_meetstream` translates the bridge's
normalized transcript response into framework-native objects. It contains no
MeetStream-specific HTTP or parsing logic itself -- that all lives in
`bridge/app/services/transcript_service.py`; this file's only job is the
transcript-segment-to-`Document` mapping and the loader's public interface.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator

from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

from langchain_meetstream.client import MeetStreamClient
from langchain_meetstream.exceptions import MeetStreamAPIError

logger = logging.getLogger(__name__)


class MeetStreamLoader(BaseLoader):
    """Loads a MeetStream meeting transcript as LangChain `Document`s.

    Example:
        ```python
        from langchain_meetstream import MeetStreamLoader

        loader = MeetStreamLoader(meeting_id="meeting_123", api_key="...")
        documents = loader.load()
        ```

    One `Document` is emitted per transcript segment (speaker turn), not one
    giant `Document` for the whole meeting. This is deliberate: it lets vector
    retrieval return the specific speaker turn relevant to a user's question,
    while keeping `speaker`/`start_time`/`end_time` as per-chunk metadata
    instead of losing that resolution by concatenating everything into one
    block of text. Downstream users who *do* want larger chunks can still run
    LangChain's own text splitters over these `Document`s (see
    `examples/rag_example.py`) -- this loader deliberately does not perform
    that chunking itself, matching the bridge's own "preserve semantic
    structure, don't pre-chunk" principle (see `docs/ARCHITECTURE.md` §7).
    """

    def __init__(
        self,
        meeting_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
        client: MeetStreamClient | None = None,
    ) -> None:
        """
        Args:
            meeting_id: The MeetStream meeting/bot id to load a transcript for.
            api_key: Passed through to `MeetStreamClient` if `client` isn't given.
            base_url: Passed through to `MeetStreamClient` if `client` isn't given.
            client: An existing `MeetStreamClient` to reuse (e.g. one already
                constructed for `get_meetstream_tools`), instead of
                constructing a new one from `api_key`/`base_url`.
        """
        self.meeting_id = meeting_id
        self._client = client or MeetStreamClient(api_key=api_key, base_url=base_url)

    def lazy_load(self) -> Iterator[Document]:
        """Yields one `Document` per transcript segment.

        Implementing `lazy_load` (rather than `load`) is the currently
        recommended `BaseLoader` pattern -- `load()`/`aload()` are provided
        for free by the base class (see `docs/ARCHITECTURE.md` §11 and §13 for
        the version this was verified against).

        Failure modes:
          - transcript not ready yet / meeting not found / auth failure /
            other bridge errors: `MeetStreamClient` already raises this
            package's own `MeetStreamAPIError` (see `client.py`), so those
            propagate to the caller unchanged -- one exception type
            regardless of which bridge error triggered it.
          - empty transcript (a real meeting with zero captured segments):
            yields nothing, not an error -- an empty transcript is a valid,
            if unusual, outcome, not a failure.
        """
        transcript = self._client.get_transcript(self.meeting_id)

        # Best-effort: enriches every segment's metadata with meeting-level
        # context (title, platform) so a retriever can filter/cite by meeting
        # without a second lookup. Fetched once per `lazy_load()` call, not
        # once per segment. `title`/`platform` are frequently `None` -- see
        # docs/ARCHITECTURE.md §6 -- but that's still more useful than
        # omitting the keys entirely, since a caller can rely on the key
        # always being present. A metadata-fetch failure does not fail the
        # whole load: the transcript itself is the primary content this
        # loader promises, and is still valid without it.
        title: str | None = None
        platform: str | None = None
        try:
            meeting = self._client.get_meeting(self.meeting_id)
            title = meeting.title
            platform = meeting.platform
        except MeetStreamAPIError as exc:
            logger.warning("Could not fetch meeting metadata for %s: %s", self.meeting_id, exc)

        for segment in transcript.segments:
            yield Document(
                page_content=segment.text,
                metadata={
                    "source": "meetstream",
                    "meeting_id": self.meeting_id,
                    "meeting_title": title,
                    "platform": platform,
                    "speaker": segment.speaker,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                },
            )
