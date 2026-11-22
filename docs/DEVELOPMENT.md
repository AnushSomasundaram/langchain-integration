# Development Guide

## Set up

```bash
git clone https://github.com/meetstream-ai/langchain-integration.git
cd langchain-integration
uv venv .venv && source .venv/bin/activate      # or python -m venv .venv
uv pip install -e ".[dev]"                      # add ,examples to run the examples
cp .env.example .env                            # only needed for the examples and notebook
```

## Test

```bash
pytest
```

The tests mock MeetStream's REST API at the `httpx` transport layer with `respx`. No network
access or MeetStream key is needed.

## Lint

```bash
ruff check langchain_meetstream tests examples
```

## Try it against your account

With `MEETSTREAM_API_KEY` set:

```bash
python examples/loader_example.py <bot id>                    # a bot whose meeting has ended
OPENAI_API_KEY=... python examples/rag_example.py <bot id> "What was decided?"
OPENAI_API_KEY=... python examples/agent_example.py <meeting url>
```

Or open [`notebooks/walkthrough.ipynb`](../notebooks/walkthrough.ipynb). It reads keys from
the environment, so nothing secret ends up in the notebook. **Clear all outputs before
committing it** (`jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`), since
outputs can contain bot ids, transcripts and participants' names.

## Build

```bash
python -m pip install build
python -m build                       # wheel + sdist in dist/
```

Check the wheel in a clean environment before publishing:

```bash
uv venv /tmp/check-lc && /tmp/check-lc/bin/pip install dist/*.whl
/tmp/check-lc/bin/python -c "from langchain_meetstream import MeetStreamLoader; print('ok')"
```

## Publish (manual)

Bump `version` in `pyproject.toml`, then `python -m build && python -m twine upload dist/*`.
