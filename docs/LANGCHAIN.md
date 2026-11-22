# LangChain Guide

How to use `langchain_meetstream`. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the design.

## Install

```bash
pip install -e .              # from the repository root
pip install -e ".[examples]"  # plus the example scripts' dependencies
```

Python 3.10+, `langchain-core` 1.x, and a MeetStream API key.

## The client

```python
from langchain_meetstream import MeetStreamClient

client = MeetStreamClient(api_key="...")   # or set MEETSTREAM_API_KEY
```

`MeetStreamClient` calls MeetStream's REST API (`https://api.meetstream.ai/api/v1`, or
`MEETSTREAM_BASE_URL`). Share one instance between the loader and the tools to reuse its
connection pool:

```python
from langchain_meetstream import MeetStreamClient, MeetStreamLoader
from langchain_meetstream.tools import get_meetstream_tools

client = MeetStreamClient()
loader = MeetStreamLoader(meeting_id="<bot id>", client=client)
tools = get_meetstream_tools(client)
```

### Transcription provider

```python
MeetStreamClient()                                            # MeetStream's own transcription (default)
MeetStreamClient(transcription_provider="deepgram",
                 transcription_options={"model": "nova-3", "language": "en"})
MeetStreamClient(transcription_provider=None)                 # bots record without a transcript

client.dispatch_bot(url, transcription_provider="assemblyai")  # per call
```

The provider applies to `dispatch_bot` and to the `dispatch_meetstream_bot` tool. Known
post-call providers are in `langchain_meetstream.TRANSCRIPTION_PROVIDERS`. Some, such as
`smallest`, need an integration key saved in the MeetStream dashboard first.

## Loading transcripts: `MeetStreamLoader`

```python
from langchain_meetstream import MeetStreamLoader

loader = MeetStreamLoader(meeting_id="<bot id>")
documents = loader.load()          # list[Document]
for doc in loader.lazy_load():     # or lazily
    ...
```

The loader emits one `Document` per transcript segment (speaker turn). Field details are in
the [README](../README.md#transcript-metadata).

What it handles:
- **Empty transcript:** yields no documents. That's not an error.
- **Items with no text:** skipped.
- **Missing speaker or times:** `None` in the metadata.
- **Errors:** raised as `MeetStreamAPIError`. `transcript_not_ready` means try again later.

Async: `await loader.aload()` and `async for doc in loader.alazy_load()` work through
LangChain's thread-executor wrapping.

## Tools: `get_meetstream_tools`

```python
tools = get_meetstream_tools(client)   # list[BaseTool], 6 tools
```

| Tool | Does |
|---|---|
| `dispatch_meetstream_bot` | Sends a bot to a meeting URL |
| `get_meeting` | The bot's current status |
| `get_meeting_transcript` | The transcript, as segments |
| `send_meeting_chat_message` | Posts in the meeting chat |
| `send_meeting_image` | Shows an image as the bot's video |
| `leave_meeting` | Makes the bot leave |

They're plain `BaseTool`s, so they work with any tool-calling agent:

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

agent = create_agent(model=ChatOpenAI(model="gpt-4o-mini"), tools=tools)
result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

Each is also importable on its own from `langchain_meetstream.tools` (`get_dispatch_bot_tool`,
`get_meeting_tool`, `get_transcript_tool`, `get_send_chat_message_tool`, `get_send_image_tool`,
`get_leave_meeting_tool`).

## RAG

[`examples/rag_example.py`](../examples/rag_example.py):

```
MeetStream → MeetStreamLoader → Documents → text splitter (optional) → embeddings → vector store → retriever → answer
```

```bash
pip install -e ".[examples]"
python examples/rag_example.py <bot id> "What deadline was discussed?"
```

## Errors

```python
from langchain_meetstream import MeetStreamAPIError

try:
    transcript = client.get_transcript("<bot id>")
except MeetStreamAPIError as exc:
    print(exc.code, exc.status_code, str(exc))
```

All codes are listed in [`exceptions.py`](../langchain_meetstream/exceptions.py).
