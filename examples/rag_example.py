"""RAG (retrieval-augmented generation) over a MeetStream meeting transcript.

Pipeline:

    MeetStream
        |
    MeetStreamLoader        (this package -- bridge-backed transcript segments)
        |
    LangChain Documents
        |
    RecursiveCharacterTextSplitter   (optional -- only if segments are long)
        |
    Embeddings
        |
    Vector store
        |
    Retriever
        |
    Question answering

The vector store used here (`langchain_core.vectorstores.InMemoryVectorStore`)
is only an example choice -- it ships with `langchain-core` itself so this
script has no extra vector-database dependency to install. The `Document`
objects `MeetStreamLoader` produces are plain LangChain `Document`s and work
with *any* LangChain-compatible vector store (Chroma, Pinecone, pgvector,
...) -- swap this one line for whichever your application already uses.

Prerequisites:
    1. The bridge server running, pointed at a real MeetStream API key.
    2. `pip install -e ".[examples]"` from this package's directory.
    3. `OPENAI_API_KEY` set (this example uses OpenAI for embeddings + chat;
       swap `OpenAIEmbeddings`/`ChatOpenAI` for any other LangChain chat/embeddings
       integration if you'd rather not use OpenAI).
    4. `MEETSTREAM_API_KEY` / `MEETSTREAM_BRIDGE_URL` set, or passed explicitly.

Run: `python examples/rag_example.py <meeting_id> "What deadline was discussed?"`
"""

from __future__ import annotations

import sys

from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_meetstream import MeetStreamLoader


def main() -> None:
    if len(sys.argv) != 3:
        print(f'Usage: python {sys.argv[0]} <meeting_id> "<question>"')
        raise SystemExit(1)
    meeting_id, question = sys.argv[1], sys.argv[2]

    documents = MeetStreamLoader(meeting_id=meeting_id).load()
    if not documents:
        print(f"No transcript segments found for meeting {meeting_id}.")
        return

    # Transcript segments from MeetStream are already speaker-turn-sized
    # chunks (see docs/ARCHITECTURE.md §7 -- the bridge deliberately doesn't
    # do generic character-based chunking). Splitting further is optional and
    # only matters if individual segments are unusually long; a 1000-char
    # chunk size is a reasonable default for spoken-language transcript text.
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    vector_store = InMemoryVectorStore(embedding=OpenAIEmbeddings(model="text-embedding-3-small"))
    vector_store.add_documents(chunks)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})

    relevant_docs = retriever.invoke(question)
    context = "\n\n".join(
        f"[{doc.metadata.get('speaker') or 'Unknown'}]: {doc.page_content}" for doc in relevant_docs
    )

    model = ChatOpenAI(model="gpt-4o-mini")
    answer = model.invoke(
        f"Answer the question using only the meeting excerpts below. "
        f"If the excerpts don't contain the answer, say so.\n\n"
        f"Meeting excerpts:\n{context}\n\nQuestion: {question}"
    )

    print(answer.content)


if __name__ == "__main__":
    main()
