# LangChain Guide

`langchain_meetstream` — native LangChain integration for MeetStream. This guide covers
usage; see [`ARCHITECTURE.md`](ARCHITECTURE.md) for design rationale and the root
[`README.md`](../README.md) for a quick reference (this doc goes deeper).

## Install

```bash
pip install -e .              # core package (run from the repo root)
pip install -e ".[examples]"  # + example-script deps
```

Requires a running [bridge server](BRIDGE_SERVER.md) and Python 3.10+. Verified against
`langchain-core==1.6.2` / `langchain==1.4.0` (see [`ARCHITECTURE.md`](ARCHITECTURE.md) §13).

## The client

```python
from langchain_meetstream import MeetStreamClient

client = MeetStreamClient(api_key="...", base_url="http://localhost:8000")
```

`api_key`/`base_url` fall back to `MEETSTREAM_API_KEY`/`MEETSTREAM_BRIDGE_URL` from the
environment if omitted. This client talks to the **bridge**, not to MeetStream — see
[`ARCHITECTURE.md`](ARCHITECTURE.md) §8a for what `api_key` means in that context.

It's shared internally between `MeetStreamLoader` and every tool in `tools/` — pass the
same `client` instance to both if you're using this integration's loader and tools
together, to reuse one connection pool:

```python
from langchain_meetstream import MeetStreamClient, MeetStreamLoader
from langchain_meetstream.tools import get_meetstream_tools

client = MeetStreamClient(api_key="...")
loader = MeetStreamLoader(meeting_id="meeting_123", client=client)
tools = get_meetstream_tools(client)
```

## Loading transcripts: `MeetStreamLoader`

```python
from langchain_meetstream import MeetStreamLoader

loader = MeetStreamLoader(meeting_id="meeting_123", api_key="...")
documents = loader.load()          # eager — list[Document]
for doc in loader.lazy_load():     # or lazily
    ...
```

A LangChain `Document` is `page_content` (a string) plus `metadata` (a dict). This loader
emits **one `Document` per transcript segment** (one speaker turn), not one `Document` for
the whole meeting — see `document_loaders/meetstream.py`'s docstring for why that matters
for retrieval. Full metadata format: see the
[root README](../README.md#transcript-metadata-format).

Handles: a completed meeting (normal case), an empty transcript (yields no `Document`s, not
an error), malformed individual segments (skipped by the bridge, not fatal — see
`ARCHITECTURE.md` §7), missing speaker/timestamps (`None` in metadata), and MeetStream/bridge
errors (raised as `MeetStreamAPIError`).

Async: `loader.aload()` / `async for doc in loader.alazy_load()` work via LangChain's
default thread-executor wrapping — see [`ARCHITECTURE.md`](ARCHITECTURE.md) §11.

## Tools: `get_meetstream_tools`

```python
from langchain_meetstream import MeetStreamClient
from langchain_meetstream.tools import get_meetstream_tools

client = MeetStreamClient(api_key="...")
tools = get_meetstream_tools(client)   # list[BaseTool], 6 tools
```

These are plain LangChain `BaseTool` objects built with `langchain_core.tools.@tool` — the
current recommended tool-authoring pattern. There is **no** separate "MeetStream agent"
class; `tools` works with any tool-calling agent:

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

agent = create_agent(model=ChatOpenAI(model="gpt-4o-mini"), tools=tools)
result = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

Individual tools are also importable if you only want a subset:
`langchain_meetstream.tools.get_dispatch_bot_tool`, `get_meeting_tool`,
`get_transcript_tool`, `get_send_chat_message_tool`, `get_send_image_tool`,
`get_leave_meeting_tool`.

## RAG

`examples/rag_example.py`:

```
MeetStream → MeetStreamLoader → Documents → RecursiveCharacterTextSplitter (optional)
    → Embeddings → Vector store → Retriever → Question answering
```

Uses `langchain_core.vectorstores.InMemoryVectorStore` (no extra dependency) — swap for any
LangChain-compatible vector store. Run:

```bash
pip install -e ".[examples]"
python examples/rag_example.py meeting_123 "What deadline was discussed?"
```

## Errors

```python
from langchain_meetstream import MeetStreamAPIError

try:
    transcript = client.get_transcript("meeting_123")
except MeetStreamAPIError as exc:
    print(exc.code, str(exc))   # e.g. "transcript_not_ready"
```

Full code list: [`BRIDGE_SERVER.md`](BRIDGE_SERVER.md#error-model).

## Examples

| File | Demonstrates |
|---|---|
| `examples/loader_example.py` | Basic `MeetStreamLoader` usage |
| `examples/rag_example.py` | Full RAG pipeline over a transcript |
| `examples/agent_example.py` | A tool-calling agent dispatching a bot and reading a transcript |
