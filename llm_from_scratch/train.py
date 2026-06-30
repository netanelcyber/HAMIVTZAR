"""
Training script for the from-scratch GPT model.

Usage
-----
    python train.py                   # train with defaults, save checkpoint
    python train.py --steps 500       # quick smoke-test

The script:
  1. Fetches Linux man-page text (or uses the built-in fallback).
  2. Trains a BPE tokeniser on that text.
  3. Trains a small GPT model using manual backprop + AdamW.
  4. Saves tokeniser and model checkpoint to ./checkpoints/.
  5. Runs a short generation demo at the end.
"""

import argparse
import random
import time
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from data import collect_corpus, TokenDataset, train_val_split
from tokenizer import BPETokenizer
from model import GPT, GPTConfig
from backprop import GPTBackward
from optimizer import AdamW


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train a from-scratch GPT on Linux docs")
    p.add_argument("--steps", type=int, default=2000, help="training steps")
    p.add_argument("--batch", type=int, default=8, help="batch size")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--vocab-size", type=int, default=1000)
    p.add_argument("--context-len", type=int, default=64)
    p.add_argument("--n-embed", type=int, default=64)
    p.add_argument("--n-heads", type=int, default=4)
    p.add_argument("--n-layers", type=int, default=2)
    p.add_argument("--man-pages", type=int, default=30, help="# Linux man pages to fetch")
    p.add_argument("--eval-every", type=int, default=200)
    p.add_argument("--gen-prompt", type=str, default="NAME", help="generation seed text")
    p.add_argument("--gen-tokens", type=int, default=60, help="tokens to generate")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out-dir", type=str, default="checkpoints")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Learning rate schedule (cosine decay with linear warmup)
# ---------------------------------------------------------------------------

def lr_schedule(step: int, total_steps: int, lr_max: float, warmup: int = 100) -> float:
    if step < warmup:
        return lr_max * step / max(warmup, 1)
    progress = (step - warmup) / max(total_steps - warmup, 1)
    return lr_max * 0.5 * (1.0 + math.cos(math.pi * progress))


# ---------------------------------------------------------------------------
# Evaluation helper
# ---------------------------------------------------------------------------

def evaluate(
    model: GPT,
    bwd: GPTBackward,
    dataset: TokenDataset,
    batch_size: int,
    n_batches: int,
    rng: random.Random,
) -> float:
    losses = []
    for _ in range(n_batches):
        x, y = dataset.random_batch(batch_size, rng)
        logits = bwd.forward(x)
        loss, _ = GPT.cross_entropy(logits, y)
        losses.append(loss)
    return float(np.mean(losses))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)
    py_rng = random.Random(args.seed)

    # ---- 1. Corpus --------------------------------------------------------
    print("Collecting Linux man-page corpus …")
    t0 = time.time()
    corpus = collect_corpus(max_pages=args.man_pages)
    print(f"  corpus: {len(corpus):,} chars  ({time.time()-t0:.1f}s)")

    # ---- 2. Tokeniser -----------------------------------------------------
    print(f"Training BPE tokeniser (vocab_size={args.vocab_size}) …")
    tok = BPETokenizer()
    tok.train(corpus, vocab_size=args.vocab_size)
    print(f"  actual vocab size: {len(tok)}")
    tok.save(str(out_dir / "tokenizer.json"))

    # ---- 3. Tokenise corpus -----------------------------------------------
    all_ids = tok.encode(corpus, add_special=False)
    print(f"  tokenised length: {len(all_ids):,}")
    if len(all_ids) < args.context_len * 2:
        raise RuntimeError("Corpus too small for context length. Reduce --context-len.")

    train_ids, val_ids = train_val_split(all_ids, val_frac=0.1)
    train_ds = TokenDataset(train_ids, args.context_len)
    val_ds = TokenDataset(val_ids, args.context_len)
    print(f"  train tokens: {len(train_ids):,}  val tokens: {len(val_ids):,}")

    # ---- 4. Model ---------------------------------------------------------
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

    # ---- 5. Training loop -------------------------------------------------
    print(f"\nTraining for {args.steps} steps …")
    history: list[dict] = []
    best_val_loss = float("inf")

    for step in range(1, args.steps + 1):
        # LR schedule
        opt.lr = lr_schedule(step, args.steps, args.lr)

        # Forward + loss
        x, y = train_ds.random_batch(args.batch, py_rng)
        logits = bwd.forward(x)
        loss, dlogits = GPT.cross_entropy(logits, y)

        # Backward
        grads = bwd.backward(dlogits)

        # Gradient clipping (max norm 1.0)
        total_norm = math.sqrt(sum(np.sum(g**2) for g in grads))
        if total_norm > 1.0:
            clip = 1.0 / total_norm
            grads = [g * clip for g in grads]

        opt.step(grads)

        if step % args.eval_every == 0 or step == args.steps:
            val_loss = evaluate(model, bwd, val_ds, args.batch, 10, py_rng)
            rec = {"step": step, "train_loss": round(loss, 4), "val_loss": round(val_loss, 4), "lr": round(opt.lr, 6)}
            history.append(rec)
            marker = " *" if val_loss < best_val_loss else ""
            print(f"  step {step:>5} | train {loss:.4f} | val {val_loss:.4f} | lr {opt.lr:.2e}{marker}")
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                _save_checkpoint(model, cfg, out_dir)

    # ---- 6. Save history --------------------------------------------------
    (out_dir / "history.json").write_text(json.dumps(history, indent=2))

    # ---- 7. Generation demo -----------------------------------------------
    print(f"\nGeneration demo (prompt: '{args.gen_prompt}') :")
    prompt_ids = tok.encode(args.gen_prompt, add_special=False)
    generated = model.generate(prompt_ids, max_new=args.gen_tokens, temperature=0.8)
    print("  " + tok.decode(generated))

    print(f"\nDone. Checkpoint saved to {out_dir}/")


def _save_checkpoint(model: GPT, cfg: GPTConfig, out_dir: Path) -> None:
    params = model.parameters()
    np.savez(str(out_dir / "model.npz"), *params)
    import dataclasses
    (out_dir / "config.json").write_text(json.dumps(dataclasses.asdict(cfg), indent=2))


if __name__ == "__main__":
    main()
