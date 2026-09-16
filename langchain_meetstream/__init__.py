"""langchain-meetstream: native LangChain integration for MeetStream.

Public API:
    - `MeetStreamClient` -- talks to the MeetStream bridge server.
    - `MeetStreamLoader` -- loads a meeting transcript as LangChain `Document`s.
    - `langchain_meetstream.tools.get_meetstream_tools` -- MeetStream tools for agents.

See the package README and the repository root `docs/ARCHITECTURE.md` for the
full design.
"""

from langchain_meetstream.client import MeetStreamClient
from langchain_meetstream.document_loaders import MeetStreamLoader
from langchain_meetstream.exceptions import MeetStreamAPIError, MeetStreamConnectionError, MeetStreamError

__version__ = "0.1.0"

__all__ = [
    "MeetStreamAPIError",
    "MeetStreamClient",
    "MeetStreamConnectionError",
    "MeetStreamError",
    "MeetStreamLoader",
]
