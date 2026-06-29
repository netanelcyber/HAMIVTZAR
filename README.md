# HAMIVTZAR — Linux Docs LLM

A small **retrieval-augmented generation (RAG)** system that answers Linux
questions grounded in a corpus of Linux documentation. It retrieves the most
relevant documentation passages with **BM25** (no embeddings service, fully
offline) and has **Claude** (`claude-opus-4-8`) write an answer that cites the
passages it used.

```
question ──▶ BM25 retrieval ──▶ top-k doc chunks ──▶ Claude ──▶ grounded, cited answer
```

## Why this design

- **Grounded answers, not hallucinations.** The model is instructed to answer
  *only* from the retrieved excerpts and to cite them as `[1]`, `[2]`, … . If
  the docs don't contain the answer, it says so instead of guessing.
- **Offline retrieval.** BM25 is implemented in pure Python — no embedding API,
  no vector database. Indexing and search work without network access.
- **Bring your own docs.** Point `ingest` at any folder of `.md`/`.rst`/`.txt`
  files (kernel docs, man pages exported to text, your team's runbooks).

## Install

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...     # required only for answering, not indexing
```

## Usage

### 1. Build the index

```bash
python -m linux_docs_llm.cli ingest
```

This indexes the sample docs in `data/docs/` into `index.json`. Use your own
corpus with `--docs`:

```bash
python -m linux_docs_llm.cli ingest --docs /path/to/your/docs
```

### 2. Ask a question

```bash
python -m linux_docs_llm.cli ask "How do I make a shell script executable?"
```

The answer streams to the terminal, followed by the list of sources it drew on.

### 3. Interactive chat

```bash
python -m linux_docs_llm.cli chat
```

### Useful flags

| Flag | Applies to | Meaning |
|------|-----------|---------|
| `--docs PATH` | `ingest` | File or directory of docs to index |
| `--target-words N` | `ingest` | Approx words per chunk (default 180) |
| `--index PATH` | all | Index file location (default `index.json`) |
| `--top-k N` | `ask`, `chat` | Number of chunks to retrieve (default 4) |
| `--model ID` | `ask`, `chat` | Claude model (default `claude-opus-4-8`) |
| `--show-retrieval` | `ask` | Print the retrieved sources before answering |
| `--no-sources` | `ask`, `chat` | Hide the trailing source list |

## Example

```text
$ python -m linux_docs_llm.cli ask "How do I restart a service and make it start at boot?"
Use `systemctl` to control the service [1]:

    sudo systemctl restart nginx      # restart now
    sudo systemctl enable nginx       # start automatically at boot

You can do both at once with `systemctl enable --now nginx` [1].

Sources:
  [1] systemd-services.md — systemctl basics  (score 12.4)
```

## Project layout

```
linux_docs_llm/
  ingest.py      Load docs and split them into heading-aware chunks
  retriever.py   Pure-Python BM25 index (build / search / save / load)
  llm.py         Prompt assembly + Claude streaming with citations
  cli.py         ingest / ask / chat commands
data/docs/       Sample Linux documentation corpus
tests/           Offline tests for ingestion + retrieval
```

## How it works

1. **Ingest** walks the docs directory, splits each file into paragraph groups
   of ~180 words, and tags each chunk with its nearest Markdown heading.
2. **Retrieve** scores every chunk against the question with BM25 and keeps the
   top-k matches (chunks that match no query term are dropped).
3. **Generate** formats the matched chunks as a numbered context block, sends it
   to Claude with a system prompt that enforces grounding + citations, and
   streams the answer back. Adaptive thinking is enabled so the model reasons
   before answering.

If retrieval finds nothing relevant, the system answers immediately without
calling the model, so it never invents an answer from thin air.

## Tests

```bash
python -m unittest discover -s tests -v
```

The test suite covers tokenization, chunking, BM25 ranking, index
save/load round-tripping, and a smoke test over the shipped corpus. It runs
fully offline (no API key needed).
