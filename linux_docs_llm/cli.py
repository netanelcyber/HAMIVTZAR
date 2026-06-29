"""Command-line interface for the Linux-docs LLM.

Commands:
    ingest  Build a BM25 index from a directory of documentation.
    ask     Answer a single question from the command line.
    chat    Interactive question/answer loop.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Tuple

from .ingest import chunk_documents, iter_documents
from .llm import DEFAULT_MODEL, LinuxDocsLLM
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
    return LinuxDocsLLM(index, model=args.model, top_k=args.top_k)


def cmd_ask(args: argparse.Namespace) -> int:
    llm = _make_llm(args)
    question = " ".join(args.question).strip()
    if not question:
        print("error: empty question", file=sys.stderr)
        return 1

    if args.show_retrieval:
        results = llm.retrieve(question)
        _print_sources(results)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linux-docs-llm",
        description="Retrieval-augmented LLM grounded in Linux documentation.",
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

    common_model = dict(
        model=dict(default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL})"),
        top_k=dict(type=int, default=4, help="number of chunks to retrieve"),
    )

    p_ask = sub.add_parser("ask", help="answer a single question")
    p_ask.add_argument("question", nargs="+", help="the question to answer")
    p_ask.add_argument("--model", **common_model["model"])
    p_ask.add_argument("--top-k", **common_model["top_k"])
    p_ask.add_argument("--no-sources", action="store_true", help="hide the source list")
    p_ask.add_argument(
        "--show-retrieval",
        action="store_true",
        help="print retrieved sources before answering",
    )
    p_ask.set_defaults(func=cmd_ask)

    p_chat = sub.add_parser("chat", help="interactive Q&A loop")
    p_chat.add_argument("--model", **common_model["model"])
    p_chat.add_argument("--top-k", **common_model["top_k"])
    p_chat.add_argument("--no-sources", action="store_true", help="hide the source list")
    p_chat.set_defaults(func=cmd_chat)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
