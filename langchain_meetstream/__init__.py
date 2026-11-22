"""langchain-meetstream: native LangChain integration for MeetStream.

Public API:
    - `MeetStreamClient` -- calls MeetStream's REST API.
    - `MeetStreamLoader` -- loads a meeting transcript as LangChain `Document`s.
    - `langchain_meetstream.tools.get_meetstream_tools` -- MeetStream tools for agents.

See the README and `docs/ARCHITECTURE.md` for the design.
"""

from langchain_meetstream.client import DEFAULT_TRANSCRIPTION_PROVIDER, TRANSCRIPTION_PROVIDERS, MeetStreamClient
from langchain_meetstream.document_loaders import MeetStreamLoader
from langchain_meetstream.exceptions import MeetStreamAPIError, MeetStreamConnectionError, MeetStreamError

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_TRANSCRIPTION_PROVIDER",
    "TRANSCRIPTION_PROVIDERS",
    "MeetStreamAPIError",
    "MeetStreamClient",
    "MeetStreamConnectionError",
    "MeetStreamError",
    "MeetStreamLoader",
]
