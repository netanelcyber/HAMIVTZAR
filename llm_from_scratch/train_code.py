"""
Train the LLM on Python code corpus (+ optional Reddit mix).

Usage:
    python train_code.py                  # train + demo
    python train_code.py --no-demo        # train only
    python train_code.py --demo-only      # load checkpoint, run demo
"""

import argparse
import random
import time
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from tokenizer import BPETokenizer
from model import GPT, GPTConfig
from backprop import GPTBackward
from optimizer import AdamW
from data import TokenDataset, train_val_split
from text_processing import preprocess_corpus


# ---------------------------------------------------------------------------
# LR schedule
# ---------------------------------------------------------------------------

def lr_schedule(step: int, total: int, lr_max: float, warmup: int = 100) -> float:
    if step < warmup:
        return lr_max * step / max(warmup, 1)
    p = (step - warmup) / max(total - warmup, 1)
    return lr_max * 0.5 * (1.0 + math.cos(math.pi * p))


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def save_checkpoint(model: GPT, cfg: GPTConfig, tok: BPETokenizer, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(str(out_dir / "model.npz"), *model.parameters())
    import dataclasses
    (out_dir / "config.json").write_text(json.dumps(dataclasses.asdict(cfg), indent=2))
    tok.save(str(out_dir / "tokenizer.json"))
    print(f"  [saved → {out_dir}/]")


def load_checkpoint(out_dir: str) -> tuple[GPT, BPETokenizer]:
    d = Path(out_dir)
    cfg = GPTConfig(**json.loads((d / "config.json").read_text()))
    model = GPT(cfg)
    data = np.load(str(d / "model.npz"))
    for p, arr in zip(model.parameters(), data.values()):
        p[:] = arr
    tok = BPETokenizer.load(str(d / "tokenizer.json"))
    return model, tok


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(args: argparse.Namespace) -> tuple[GPT, BPETokenizer]:
    out_dir = Path(args.out_dir)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)

    # Load corpora
    code_path = Path("data/python_code_corpus.txt")
    reddit_path = Path("data/reddit_corpus.txt")

    parts = []
    if code_path.exists():
        code_text = code_path.read_text(encoding="utf-8", errors="replace")
        print(f"  Code corpus:   {len(code_text):,} chars")
        parts.append(code_text)
    else:
        print("  WARNING: data/python_code_corpus.txt not found")

    if reddit_path.exists() and args.reddit_mix > 0:
        reddit_text = reddit_path.read_text(encoding="utf-8", errors="replace")
        # Take only a fraction of reddit to keep code dominant
        keep = int(len(reddit_text) * args.reddit_mix)
        reddit_text = reddit_text[:keep]
        print(f"  Reddit corpus: {len(reddit_text):,} chars ({args.reddit_mix:.0%} of full)")
        parts.append(reddit_text)

    corpus = "\n\n".join(parts)
    print(f"  Total corpus:  {len(corpus):,} chars")

    # Light cleaning (preserve indentation — critical for Python)
    print("Cleaning corpus (preserving indentation) …")
    # Only strip null bytes and carriage returns; keep all whitespace structure
    corpus = corpus.replace("\r\n", "\n").replace("\r", "\n")
    corpus = "".join(ch for ch in corpus if ch >= " " or ch in "\n\t")
    print(f"  Cleaned:       {len(corpus):,} chars")

    # Tokenizer — train on full corpus (it's small enough)
    print(f"Training BPE (vocab_size={args.vocab_size}) …")
    tok = BPETokenizer()
    tok.train(corpus, vocab_size=args.vocab_size)
    print(f"  vocab: {len(tok)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    tok.save(str(out_dir / "tokenizer.json"))

    # Encode
    print("Encoding corpus …")
    chunk = 50_000
    all_ids: list[int] = []
    for i in range(0, len(corpus), chunk):
        all_ids.extend(tok.encode(corpus[i:i+chunk], add_special=False))
        if (i // chunk) % 5 == 0:
            print(f"  {i:,}/{len(corpus):,} chars → {len(all_ids):,} tokens", end="\r")
    print(f"  Total tokens: {len(all_ids):,}          ")

    if len(all_ids) < args.context_len * 4:
        raise RuntimeError("Corpus too small. Reduce --context-len.")

    train_ids, val_ids = train_val_split(all_ids, val_frac=0.1)
    train_ds = TokenDataset(train_ids, args.context_len)
    val_ds   = TokenDataset(val_ids,   args.context_len)

    # Model
    cfg = GPTConfig(
        vocab_size=len(tok),
        context_len=args.context_len,
        n_embed=args.n_embed,
        n_heads=args.n_heads,
        n_layers=args.n_layers,
        seed=args.seed,
    )
    model = GPT(cfg)
    bwd   = GPTBackward(model)
    n_params = sum(p.size for p in model.parameters())
    print(f"  model params: {n_params:,}")
    opt = AdamW(model.parameters(), lr=args.lr)

    # Training loop
    print(f"\nTraining {args.steps} steps …")
    best_val = float("inf")
    t0 = time.time()
    for step in range(1, args.steps + 1):
        opt.lr = lr_schedule(step, args.steps, args.lr)
        x, y = train_ds.random_batch(args.batch, rng)
        logits = bwd.forward(x)
        loss, dlogits = GPT.cross_entropy(logits, y)
        grads = bwd.backward(dlogits)
        norm = math.sqrt(sum(float(np.sum(g**2)) for g in grads))
        if norm > 1.0:
            grads = [g / norm for g in grads]
        opt.step(grads)

        if step % args.eval_every == 0 or step == args.steps:
            vlosses = []
            for _ in range(8):
                vx, vy = val_ds.random_batch(args.batch, rng)
                vl, _ = GPT.cross_entropy(bwd.forward(vx), vy)
                vlosses.append(float(vl))
            val_loss = float(np.mean(vlosses))
            elapsed = time.time() - t0
            mark = " *" if val_loss < best_val else ""
            print(f"  step {step:>5} | train {loss:.4f} | val {val_loss:.4f} | lr {opt.lr:.2e} | {elapsed:.0f}s{mark}")
            if val_loss < best_val:
                best_val = val_loss
                save_checkpoint(model, cfg, tok, out_dir)

    print(f"\nBest val_loss: {best_val:.4f}  Checkpoint: {out_dir}/")
    return model, tok


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

CODE_PROMPTS = [
    "def fibonacci(n):",
    "def bubble_sort(arr):",
    "class Stack:",
    "def binary_search(arr, target):",
    "def is_palindrome(s):",
    "# Calculate factorial\ndef factorial(n):",
    "import math\n\ndef gcd(a, b):",
    "def merge_sort(arr):",
]

def run_demo(model: GPT, tok: BPETokenizer) -> None:
    print("\n" + "="*60)
    print("  Code LLM — Generation Demo")
    print("="*60)
    for prompt in CODE_PROMPTS:
        ids = tok.encode(prompt, add_special=False)
        generated = model.generate(ids, max_new=100, temperature=0.7)
        output = tok.decode(generated)
        print(f"\nPrompt: {prompt!r}")
        print(f"Output:\n{output}")
        print("-"*40)


# ---------------------------------------------------------------------------
# Interactive chat
# ---------------------------------------------------------------------------

def chat(model: GPT, tok: BPETokenizer) -> None:
    print("\n" + "="*60)
    print("  Code LLM — Interactive")
    print("  Type a Python prompt, 'quit' to exit.")
    print("="*60 + "\n")
    while True:
        try:
            prompt = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not prompt or prompt.lower() in ("quit", "exit", "q"):
            break
        ids = tok.encode(prompt, add_special=False)
        out = model.generate(ids, max_new=150, temperature=0.7)
        print(tok.decode(out))
        print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--steps",       type=int,   default=5000)
    p.add_argument("--batch",       type=int,   default=16)
    p.add_argument("--lr",          type=float, default=3e-4)
    p.add_argument("--vocab-size",  type=int,   default=1000)
    p.add_argument("--context-len", type=int,   default=128)
    p.add_argument("--n-embed",     type=int,   default=128)
    p.add_argument("--n-heads",     type=int,   default=4)
    p.add_argument("--n-layers",    type=int,   default=4)
    p.add_argument("--eval-every",  type=int,   default=500)
    p.add_argument("--seed",        type=int,   default=42)
    p.add_argument("--out-dir",     type=str,   default="checkpoints_code")
    p.add_argument("--reddit-mix",  type=float, default=0.0,
                   help="Fraction of Reddit corpus to mix in (0=none, 1=all)")
    p.add_argument("--no-demo",     action="store_true")
    p.add_argument("--demo-only",   action="store_true")
    p.add_argument("--chat",        action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.demo_only:
        print("Loading checkpoint …")
        model, tok = load_checkpoint(args.out_dir)
    else:
        model, tok = train(args)

    if not args.no_demo:
        run_demo(model, tok)

    if args.chat:
        chat(model, tok)


if __name__ == "__main__":
    main()
