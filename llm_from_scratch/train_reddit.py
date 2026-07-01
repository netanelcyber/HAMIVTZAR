"""
Train the LLM specifically on Reddit corpus then launch an interactive chat.

Sources:
  - data/reddit_corpus.txt (downloaded from GitHub: minimaxir/textgenrnn datasets)
    Contains real Reddit posts from: r/politics, r/rarepuppers, r/apple,
    r/android, r/relationship_advice, r/legaladvice + Hacker News

Usage:
    python train_reddit.py            # train + chat
    python train_reddit.py --no-chat  # train only
    python train_reddit.py --chat-only  # skip training, load checkpoint
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
# Helpers
# ---------------------------------------------------------------------------

def lr_schedule(step: int, total: int, lr_max: float, warmup: int = 50) -> float:
    if step < warmup:
        return lr_max * step / max(warmup, 1)
    p = (step - warmup) / max(total - warmup, 1)
    return lr_max * 0.5 * (1.0 + math.cos(math.pi * p))


def load_reddit_corpus(path: str = "data/reddit_corpus.txt") -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"{path} not found. Run the download step first or run train.py."
        )
    text = p.read_text(encoding="utf-8", errors="replace")
    print(f"  Reddit corpus: {len(text):,} chars from {path}")
    return text


def save_checkpoint(model: GPT, cfg: GPTConfig, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(str(out_dir / "model.npz"), *model.parameters())
    import dataclasses
    (out_dir / "config.json").write_text(json.dumps(dataclasses.asdict(cfg), indent=2))


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

    # Corpus
    print("Loading Reddit corpus …")
    corpus = load_reddit_corpus("data/reddit_corpus.txt")

    print("Pre-processing with NLTK …")
    corpus, stats = preprocess_corpus(corpus, analyze=True)
    if stats:
        top5 = ", ".join(f"{w}({c})" for w, c in stats["top_content_words"][:5])
        print(f"  words={stats['total_words']:,}  unique={stats['unique_words']:,}  top: {top5}")
    print(f"  cleaned: {len(corpus):,} chars")

    # Tokeniser
    print(f"Training BPE (vocab_size={args.vocab_size}) …")
    tok = BPETokenizer()
    tok.train(corpus, vocab_size=args.vocab_size)
    print(f"  vocab: {len(tok)}")
    out_dir.mkdir(parents=True, exist_ok=True)
    tok.save(str(out_dir / "tokenizer.json"))

    # Tokenise
    all_ids = tok.encode(corpus, add_special=False)
    print(f"  tokens: {len(all_ids):,}")
    if len(all_ids) < args.context_len * 4:
        raise RuntimeError("Corpus too small. Reduce --context-len.")

    train_ids, val_ids = train_val_split(all_ids, val_frac=0.1)
    train_ds = TokenDataset(train_ids, args.context_len)
    val_ds = TokenDataset(val_ids, args.context_len)

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
    bwd = GPTBackward(model)
    params = model.parameters()
    n_params = sum(p.size for p in params)
    print(f"  model params: {n_params:,}")
    opt = AdamW(params, lr=args.lr)

    # Training loop
    print(f"\nTraining {args.steps} steps on Reddit …")
    best_val = float("inf")
    for step in range(1, args.steps + 1):
        opt.lr = lr_schedule(step, args.steps, args.lr)
        x, y = train_ds.random_batch(args.batch, rng)
        logits = bwd.forward(x)
        loss, dlogits = GPT.cross_entropy(logits, y)
        grads = bwd.backward(dlogits)
        norm = math.sqrt(sum(np.sum(g**2) for g in grads))
        if norm > 1.0:
            grads = [g / norm for g in grads]
        opt.step(grads)

        if step % args.eval_every == 0 or step == args.steps:
            # val loss
            vlosses = []
            for _ in range(8):
                vx, vy = val_ds.random_batch(args.batch, rng)
                vlogits = bwd.forward(vx)
                vl, _ = GPT.cross_entropy(vlogits, vy)
                vlosses.append(vl)
            val_loss = float(np.mean(vlosses))
            mark = " *" if val_loss < best_val else ""
            print(f"  step {step:>5} | train {loss:.4f} | val {val_loss:.4f} | lr {opt.lr:.2e}{mark}")
            if val_loss < best_val:
                best_val = val_loss
                save_checkpoint(model, cfg, out_dir)

    print(f"\nBest val_loss: {best_val:.4f}  Checkpoint: {out_dir}/")
    return model, tok


# ---------------------------------------------------------------------------
# Interactive chat
# ---------------------------------------------------------------------------

def chat(model: GPT, tok: BPETokenizer) -> None:
    print("\n" + "="*60)
    print("  Reddit LLM — interactive chat")
    print("  Type a prompt and press Enter. 'quit' to exit.")
    print("="*60 + "\n")

    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        ids = tok.encode(prompt, add_special=False)
        generated = model.generate(ids, max_new=120, temperature=0.85)
        response = tok.decode(generated[len(ids):])
        print(f"\nLLM: {response}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--vocab-size", type=int, default=1500)
    p.add_argument("--context-len", type=int, default=64)
    p.add_argument("--n-embed", type=int, default=128)
    p.add_argument("--n-heads", type=int, default=4)
    p.add_argument("--n-layers", type=int, default=3)
    p.add_argument("--eval-every", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", type=str, default="checkpoints_reddit")
    p.add_argument("--no-chat", action="store_true")
    p.add_argument("--chat-only", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.chat_only:
        print("Loading checkpoint …")
        model, tok = load_checkpoint(args.out_dir)
    else:
        model, tok = train(args)

    if not args.no_chat:
        chat(model, tok)


if __name__ == "__main__":
    main()
