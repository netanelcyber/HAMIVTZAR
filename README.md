# HAMIVTZAR — Linux Docs LLM

A small **retrieval-augmented generation (RAG)** system that answers Linux
questions grounded in a corpus of Linux documentation. It is **offline-first**:
out of the box it runs **fully disconnected** — no network, no API key, no model
download. Retrieval uses pure-Python **BM25**, and the default answer engine
builds the reply directly from the retrieved docs. A real local LLM (Ollama or
llama.cpp) can be plugged in, also fully offline. Claude is an optional online
backend you must select explicitly.

```
question ──▶ BM25 retrieval ──▶ top-k doc chunks ──▶ answer backend ──▶ grounded, cited answer
```

## Offline by default

`--backend auto` (the default) only ever selects a **local, disconnected**
engine. It never touches the network. It picks the first one that is available:

| Backend | Offline | Needs | What it is |
|---------|:------:|-------|------------|
| `extractive` | ✅ | nothing (stdlib only) | Builds the answer from the retrieved passages. Always works. |
| `ollama` | ✅ | local [Ollama](https://ollama.com) daemon + a pulled model | A real local LLM via the daemon's HTTP API. |
| `llama-cpp` | ✅ | `llama-cpp-python` + a local GGUF file | A real local LLM in-process. |
| `claude` | ❌ | network + `ANTHROPIC_API_KEY` | Anthropic API. **Opt-in only**; `auto` never picks it. |

If a backend you select explicitly isn't available (no daemon, missing library,
no API key), the system prints a notice and **falls back to `extractive`** so it
keeps working disconnected.

## Why this design

- **Works disconnected.** The whole pipeline — indexing, retrieval, and
  answering — runs with no network and no third-party packages.
- **Grounded answers, not hallucinations.** Answers come only from the retrieved
  excerpts and cite them as `[1]`, `[2]`, … . If the docs don't contain the
  answer, the system says so instead of guessing.
- **Bring your own docs.** Point `ingest` at any folder of `.md`/`.rst`/`.txt`
  files (kernel docs, man pages exported to text, your team's runbooks).

## Install

```bash
# Core + the default offline backend need no third-party packages.
git clone <this repo> && cd HAMIVTZAR
```

Optional, only if you want a local LLM backend:

```bash
# Option A: Ollama (recommended local LLM, fully offline once pulled)
#   install from https://ollama.com, then:
ollama pull llama3.2

# Option B: llama.cpp with a local GGUF model
pip install "llama-cpp-python>=0.2"

# Option C: Claude (online, opt-in)
pip install "anthropic>=0.40" && export ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

### 1. Build the index (offline)

```bash
python -m linux_docs_llm.cli ingest
```

Indexes the sample docs in `data/docs/` into `index.json`. Use your own corpus
with `--docs /path/to/your/docs`.

### 2. Ask a question (offline by default)

```bash
python -m linux_docs_llm.cli ask "How do I make a shell script executable?"
```

The answer streams to the terminal, followed by the sources it used. The chosen
backend is printed to stderr, e.g. `[backend: extractive]`.

### 3. Use a local LLM (still offline)

```bash
# Ollama
python -m linux_docs_llm.cli ask "How do I restart a service at boot?" \
    --backend ollama --ollama-model llama3.2

# llama.cpp
python -m linux_docs_llm.cli ask "How do I restart a service at boot?" \
    --backend llama-cpp --model-path ./models/qwen2.5-1.5b-instruct-q4_k_m.gguf
```

### 4. Interactive chat

```bash
python -m linux_docs_llm.cli chat            # offline (auto)
python -m linux_docs_llm.cli chat --backend ollama
```

### Flags

| Flag | Applies to | Meaning |
|------|-----------|---------|
| `--docs PATH` | `ingest` | File or directory of docs to index |
| `--target-words N` | `ingest` | Approx words per chunk (default 180) |
| `--index PATH` | all | Index file location (default `index.json`) |
| `--backend NAME` | `ask`, `chat` | `auto` (default), `extractive`, `ollama`, `llama-cpp`, `claude` |
| `--top-k N` | `ask`, `chat` | Number of chunks to retrieve (default 4) |
| `--ollama-model NAME` | `ask`, `chat` | Ollama model (default `llama3.2`) |
| `--ollama-url URL` | `ask`, `chat` | Ollama base URL (default `http://localhost:11434`) |
| `--model-path PATH` | `ask`, `chat` | GGUF model file for `llama-cpp` |
| `--model ID` | `ask`, `chat` | Claude model id for `--backend claude` |
| `--show-retrieval` | `ask` | Print the retrieved sources before answering |
| `--no-sources` | `ask`, `chat` | Hide the trailing source list |

## Example (offline, extractive)

```text
$ python -m linux_docs_llm.cli ask "How do I make a shell script executable?"
[backend: extractive]
Based on the Linux documentation [1]:

    chmod u+x script.sh      # make the file executable for its owner
    chmod go-w file.txt      # remove write for group and others
    chmod a=r file.txt       # set everyone to read-only

Related sections:
  [2] file-permissions.md — Special bits
  ...

Sources:
  [1] file-permissions.md — Changing permissions with chmod  (score 6.99)
```

## Project layout

```
linux_docs_llm/
  ingest.py      Load docs and split them into heading-aware chunks
  retriever.py   Pure-Python BM25 index (build / search / save / load)
  prompt.py      Shared system prompt + context formatting
  backends.py    Answer engines: extractive / ollama / llama-cpp / claude
  llm.py         Retrieve chunks and answer with the chosen backend
  cli.py         ingest / ask / chat commands
data/docs/                        Sample Linux documentation corpus
iso27001-book/                    Hebrew summary book on ISO/IEC 27001 and the ISO/IEC 27000 family
  README.md                         Table of contents / cover page
  01..07-*.md                       Chapters: intro, clauses 4-10, Annex A controls, derivative
                                     standards, certification process, practical rollout, 2013 vs 2022
  08-milon-munachim-vecheck-list.md Glossary + implementation/certification checklist
  09-pentesting-veiso27001.md        Pentesting chapter: maps pentest to Annex A controls, test types,
                                     methodologies (PTES/OWASP/NIST/OSSTMM/CompTIA PenTest+), ROE/ethics,
                                     a worked example converting this repo's own pentest-milatova findings
                                     into a risk register, international standards (CREST/TIBER-EU/DORA)
                                     and Israeli regulatory context
  10-protokolim-mefurtim-cwe.md      Detailed step-by-step testing protocol for each of the 41 CWEs
  11-zero-day-research.md            Zero-day discovery methodology framed for risk management (fuzzing,
                                     code review, patch diffing, coordinated disclosure), not exploit dev
  tools/cwe_risk_calculator.py      Offline CWE-informed Likelihood x Impact risk scorer (ISO/IEC 27005-style)
  tools/README.md                   Also documents ready-made static-analysis tools for manual triage of a
                                     suspicious PHP/Python/JS-TS file (Semgrep, YARA + PHP-Malware-Finder,
                                     Bandit, ESLint-security) -- deliberately not reimplemented in this repo
security_classifier/              Defensive static + optional dynamic classifier for Python code
  features.py                       Static AST-based feature extraction (never executes code)
  dynamic_features.py               Parses a runtime trace you collected (never executes code)
  dataset.py / train.py / analyze.py   Dataset assembly, training, cross-validated analytics
  classify.py / explain.py          Score a file; natural-language summary of the finding
scripts/fetch_benign_corpus.py    Clones legitimate SDKs for classifier training data
scripts/sandboxed_trace.sh        Template: collect a runtime trace on YOUR isolated sandbox
tests/                            Offline tests for ingestion, retrieval, backends, and the classifier
```

## How it works

1. **Ingest** walks the docs directory, splits each file into paragraph groups
   of ~180 words, and tags each chunk with its nearest Markdown heading.
2. **Retrieve** scores every chunk against the question with BM25 and keeps the
   top-k matches (chunks that match no query term are dropped).
3. **Answer** hands the matched chunks to the selected backend:
   - `extractive` picks the most query-relevant sentences and command blocks
     from the top chunk and cites them — no model, no network.
   - `ollama` / `llama-cpp` send a grounded, citation-enforcing prompt to a
     local LLM and stream the reply.
   - `claude` does the same via the Anthropic API (online).

If retrieval finds nothing relevant, the system answers immediately without
calling any backend, so it never invents an answer from thin air.

## Security classifier

`security_classifier/` is a separate, defensive tool: a static-analysis
classifier that flags structurally suspicious Python files (suspicious
imports, dynamic execution, obfuscation, network/persistence indicators). It
never executes the code it analyzes — only `ast.parse` and string inspection.

**Data sourcing is deliberate and scoped:**

- **Benign class** — real Python source *you* fetch yourself. Run
  `python scripts/fetch_benign_corpus.py` to `git clone` a small allowlist of
  legitimate, permissively-licensed security-vendor SDKs (seeded with
  [CrowdStrike FalconPy](https://github.com/CrowdStrike/falconpy), Unlicense)
  into `data/security/benign/`. Nothing is fetched automatically — you run
  this script, on your machine, when you choose to.
- **Malicious class** — must be real, labeled samples *you* supply in an
  isolated directory via `--malicious-dir`. Without one, a small hand-authored
  set of **synthetic feature vectors** (numbers, not code) stands in so the
  pipeline runs end to end — see the module docstring in `dataset.py` for
  exactly what that placeholder is and isn't.
- This module does not fetch, vendor, or train on offensive/exploitation
  tooling or unvetted "attack code" scraped from the internet.

```bash
pip install scikit-learn joblib

# optional: fetch real benign training data
python scripts/fetch_benign_corpus.py

# train (uses synthetic placeholders for any class with no --*-dir given)
python -m security_classifier.train --benign-dir data/security/benign/falconpy

# score a file or directory
python -m security_classifier.classify path/to/file_or_dir.py

# also summarize what each file appears to do, in plain language
python -m security_classifier.classify path/to/file_or_dir.py --explain

# analytics report: cross-validated per-sample scores, class statistics,
# and feature importances over whatever data is currently configured
python -m security_classifier.analyze
```

**`--explain`** turns a finding into a natural-language summary of what the
code structurally appears to do (imports, dynamic execution, network/
persistence indicators) and why it scored the way it did — for benign and
malicious verdicts alike. The model is only ever shown the extracted feature
values, never the raw source. Offline-first, same as `linux_docs_llm`:
`--explain-backend auto` (default) tries a local LLM (Ollama, then llama.cpp)
and always falls back to a deterministic, dependency-free template if none is
available — so it produces a summary even fully disconnected. `claude` is
opt-in only (`--explain-backend claude`) and is never selected by `auto`.

`analyze` never fetches or generates new code samples — it only reports on
data already in the pipeline (real directories if given, the synthetic
placeholder set otherwise), and scores each sample with a model that did not
train on it (cross-validation), so the report isn't just memorized accuracy.

With only the synthetic placeholder data on both sides, the model is a
pipeline demo, not an accurate classifier — in testing it even flagged this
repo's own `linux_docs_llm/backends.py` as suspicious (a real false-positive
bug, since fixed — see `security_classifier/features.py`'s handling of
`eval`/`exec`/`compile`). Real accuracy requires real, representative samples
for both classes.

**Static analysis alone has real limits.** Scanning
[sqlmap](https://github.com/sqlmapproject/sqlmap) (a legitimate, widely-used
pentest tool — not malware) flagged 80/589 files, and the top hits were mostly
false positives: a self-update mechanism using `subprocess(shell=True)`, a
Windows-compat shim using `ctypes`+`socket`, a git-revision lookup, and a
deliberately-vulnerable test fixture bundled for sqlmap's own test suite.
Structural patterns alone can't distinguish "does this dangerous-looking
thing" from "actually attacks something."

### Dynamic (behavioral) analysis — optional, and never executed by this project

`security_classifier/dynamic_features.py` adds a second signal: what code
*actually does* at runtime (network connections, file writes, processes
spawned), parsed from a trace **you** collect. This module and everything else
in this repository **never executes the code being analyzed** — that
execution step must happen on infrastructure you control, fully isolated from
this project's own environment.

```bash
# On YOUR OWN disposable, network-isolated machine — never here:
./scripts/sandboxed_trace.sh path/to/suspect.py trace.jsonl

# Then, back wherever you're running the classifier:
python -m security_classifier.classify path/to/suspect.py --explain --trace trace.jsonl
```

`scripts/sandboxed_trace.sh` is a heavily-commented template (Docker,
`--network none`, dropped capabilities, a hard timeout, `strace`) for
collecting that trace safely — read its warning header before using it. When a
trace is supplied, `--explain` treats observed behavior (an actual outbound
connection, an actual write to an autostart location) as stronger evidence
than static structure alone.

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers tokenization, chunking, BM25 ranking, index save/load round-tripping,
the extractive backend, backend resolution (including that `auto` never
selects the online Claude backend), and the security classifier's feature
extraction / dataset assembly / training pipeline. Runs fully offline; the two
end-to-end training tests skip automatically if `scikit-learn`/`joblib` aren't
installed.
