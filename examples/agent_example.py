"""A LangChain tool-calling agent with MeetStream capabilities.

Demonstrates the "AI -> Meeting" direction: a user asks a normal LangChain
agent (built with `langchain.agents.create_agent`, the current recommended
tool-calling agent constructor) to do something involving MeetStream, and the
agent decides on its own which MeetStream tool to call, e.g.:

    User: "Send a bot to <meeting url> and tell me its meeting ID."
    Agent -> calls dispatch_meetstream_bot(meeting_url=..., bot_name=...)
    Agent -> replies with the bot_id from the tool's result

There is no special "MeetStream agent" class here -- `get_meetstream_tools`
just returns plain `BaseTool` objects that work with any LangChain
tool-calling agent.

Prerequisites:
    1. `pip install -e ".[examples]"` from the repository root.
    2. `MEETSTREAM_API_KEY` set.
    3. `OPENAI_API_KEY` set (or swap `ChatOpenAI` for any other LangChain
       tool-calling chat model).

Run: `python examples/agent_example.py <meeting url> [<bot id with a finished transcript>]`
"""

from __future__ import annotations

import sys

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from langchain_meetstream import MeetStreamClient
from langchain_meetstream.tools import get_meetstream_tools


def main() -> None:
    if len(sys.argv) not in (2, 3):
        print(f"Usage: python {sys.argv[0]} <meeting url> [<bot id with a finished transcript>]")
        raise SystemExit(1)
    meeting_url = sys.argv[1]
    finished_bot_id = sys.argv[2] if len(sys.argv) == 3 else None

    client = MeetStreamClient()  # reads MEETSTREAM_API_KEY; bots use MeetStream's own transcription
    tools = get_meetstream_tools(client)

    agent = create_agent(model=ChatOpenAI(model="gpt-4o-mini"), tools=tools)

    # 1. Dispatch a bot into a meeting.
    result = agent.invoke(
        {"messages": [{"role": "user", "content": f"Send a MeetStream bot to {meeting_url} and tell me its meeting ID."}]}
    )
    print("Agent:", result["messages"][-1].content)

    # 2. Retrieve a transcript. Transcription is asynchronous on MeetStream's
    # side -- this example deliberately does
    # NOT poll in a loop waiting for it to finish. If you ask the agent to
    # fetch a transcript before MeetStream has finished processing it, the
    # `get_meeting_transcript` tool will raise a `transcript_not_ready` error,
    # which the agent will typically report back to you rather than silently
    # retrying forever; ask again once the meeting has ended and a short
    # processing delay has passed.
    if finished_bot_id:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": f"What did people say in meeting {finished_bot_id}? Summarize the key points."}]}
        )
        print("Agent:", result["messages"][-1].content)


if __name__ == "__main__":
    main()
