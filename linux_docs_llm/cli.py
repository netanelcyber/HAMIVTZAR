"""Command-line interface for the Linux-docs LLM.

Commands:
    ingest  Build a BM25 index from a directory of documentation.
    ask     Answer a single question from the command line.
    chat    Interactive question/answer loop.

Answering is offline by default: the ``auto`` backend selects an available
local engine (Ollama / llama.cpp / extractive) and never touches the network.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

from .backends import BACKEND_NAMES, DEFAULT_CLAUDE_MODEL, ExtractiveAnswerer, resolve_backend
from .ingest import chunk_documents, iter_documents
from .llm import LinuxDocsLLM
from .retriever import BM25Index

DEFAULT_INDEX = "index.json"
DEFAULT_DOCS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "docs")


def cmd_ingest(args: argparse.Namespace) -> int:
    if not os.path.exists(args.docs):
        print(f"error: docs path not found: {args.docs}", file=sys.stderr)
        return 1
    documents = list(iter_documents(args.docs))
    if not documents:
        print(f"error: no documentation files under {args.docs}", file=sys.stderr)
        return 1
    chunks = chunk_documents(documents, target_words=args.target_words)
    index = BM25Index(chunks)
    index.save(args.index)
    print(
        f"Indexed {len(documents)} document(s) into {len(chunks)} chunk(s) "
        f"-> {args.index}"
    )
    return 0


def _load_index(path: str) -> BM25Index:
    if not os.path.exists(path):
        print(
            f"error: index not found: {path}\n"
            f"Run `python -m linux_docs_llm.cli ingest` first.",
            file=sys.stderr,
        )
        sys.exit(1)
    return BM25Index.load(path)


def _print_sources(results: List[Tuple]) -> None:
    if not results:
        return
    print("\n\nSources:")
    for n, (chunk, score) in enumerate(results, start=1):
        label = chunk.source + (f" — {chunk.heading}" if chunk.heading else "")
        print(f"  [{n}] {label}  (score {score:.2f})")


def _make_llm(args: argparse.Namespace) -> LinuxDocsLLM:
    index = _load_index(args.index)
    backend = resolve_backend(
        args.backend,
        ollama_model=getattr(args, "ollama_model", "llama3.2"),
        ollama_url=getattr(args, "ollama_url", None),
        model_path=getattr(args, "model_path", None),
        model=getattr(args, "model", DEFAULT_CLAUDE_MODEL),
    )
    # An explicitly chosen backend that can't run (no server / missing lib /
    # no API key) must not crash — degrade to the always-offline extractive one.
    if args.backend != "auto" and not backend.available():
        print(
            f"[backend: {backend.name} unavailable — falling back to extractive]",
            file=sys.stderr,
        )
        backend = ExtractiveAnswerer()
    print(f"[backend: {backend.name}]", file=sys.stderr)
    return LinuxDocsLLM(index, backend=backend, top_k=args.top_k)


def cmd_ask(args: argparse.Namespace) -> int:
    llm = _make_llm(args)
    question = " ".join(args.question).strip()
    if not question:
        print("error: empty question", file=sys.stderr)
        return 1

    if args.show_retrieval:
        _print_sources(llm.retrieve(question))
        print()

    _answer, results = llm.answer(question, on_text=lambda t: print(t, end="", flush=True))
    if not args.no_sources:
        _print_sources(results)
    print()
    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    llm = _make_llm(args)
    print("Linux docs assistant. Ask a question, or type 'exit' to quit.\n")
    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit", ":q"}:
            break
        if not question:
            continue
        print("\nassistant> ", end="", flush=True)
        _answer, results = llm.answer(question, on_text=lambda t: print(t, end="", flush=True))
        if not args.no_sources:
            _print_sources(results)
        print("\n")
    return 0


def _add_answer_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend",
        choices=BACKEND_NAMES,
        default="auto",
        help="answer engine (default: auto — offline local engine, never network)",
    )
    parser.add_argument("--top-k", type=int, default=4, help="number of chunks to retrieve")
    parser.add_argument("--no-sources", action="store_true", help="hide the source list")
    # Ollama backend
    parser.add_argument("--ollama-model", default="llama3.2", help="Ollama model name")
    parser.add_argument("--ollama-url", default=None, help="Ollama base URL")
    # llama.cpp backend
    parser.add_argument("--model-path", default=None, help="path to a local GGUF model")
    # Claude backend (online, opt-in)
    parser.add_argument(
        "--model", default=DEFAULT_CLAUDE_MODEL, help="Claude model id (--backend claude)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linux-docs-llm",
        description="Offline-first retrieval-augmented LLM grounded in Linux documentation.",
    )
    parser.add_argument(
        "--index", default=DEFAULT_INDEX, help=f"index file (default: {DEFAULT_INDEX})"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="build the BM25 index from docs")
    p_ingest.add_argument(
        "--docs", default=DEFAULT_DOCS, help="docs file or directory to index"
    )
    p_ingest.add_argument(
        "--target-words", type=int, default=180, help="approx words per chunk"
    )
    p_ingest.set_defaults(func=cmd_ingest)

    p_ask = sub.add_parser("ask", help="answer a single question")
    p_ask.add_argument("question", nargs="+", help="the question to answer")
    p_ask.add_argument(
        "--show-retrieval",
        action="store_true",
        help="print retrieved sources before answering",
    )
    _add_answer_args(p_ask)
    p_ask.set_defaults(func=cmd_ask)

    p_chat = sub.add_parser("chat", help="interactive Q&A loop")
    _add_answer_args(p_chat)
    p_chat.set_defaults(func=cmd_chat)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
