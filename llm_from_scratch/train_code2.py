"""
Train LLM on programming corpus: Python code + Python docs + Hacker News.
"""

import random, time, json, math, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from tokenizer import BPETokenizer
from model import GPT, GPTConfig
from backprop import GPTBackward
from optimizer import AdamW
from data import TokenDataset, train_val_split


def lr_schedule(step, total, lr_max, warmup=200):
    if step < warmup:
        return lr_max * step / max(warmup, 1)
    p = (step - warmup) / max(total - warmup, 1)
    return lr_max * 0.5 * (1.0 + math.cos(math.pi * p))


def save_ckpt(model, cfg, tok, out_dir):
    import dataclasses
    out_dir.mkdir(parents=True, exist_ok=True)
    np.savez(str(out_dir / "model.npz"), *model.parameters())
    (out_dir / "config.json").write_text(json.dumps(dataclasses.asdict(cfg), indent=2))
    tok.save(str(out_dir / "tokenizer.json"))


def load_ckpt(out_dir):
    d = Path(out_dir)
    cfg = GPTConfig(**json.loads((d / "config.json").read_text()))
    model = GPT(cfg)
    data = np.load(str(d / "model.npz"))
    for p, arr in zip(model.parameters(), data.values()):
        p[:] = arr
    tok = BPETokenizer.load(str(d / "tokenizer.json"))
    return model, tok


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--steps",       type=int,   default=8000)
    p.add_argument("--batch",       type=int,   default=16)
    p.add_argument("--lr",          type=float, default=3e-4)
    p.add_argument("--vocab-size",  type=int,   default=2000)
    p.add_argument("--context-len", type=int,   default=128)
    p.add_argument("--n-embed",     type=int,   default=192)
    p.add_argument("--n-heads",     type=int,   default=4)
    p.add_argument("--n-layers",    type=int,   default=4)
    p.add_argument("--eval-every",  type=int,   default=500)
    p.add_argument("--seed",        type=int,   default=42)
    p.add_argument("--out-dir",     type=str,   default="checkpoints_code2")
    p.add_argument("--demo-only",   action="store_true")
    args = p.parse_args()

    out_dir = Path(args.out_dir)

    if args.demo_only:
        model, tok = load_ckpt(args.out_dir)
    else:
        np.random.seed(args.seed)
        rng = random.Random(args.seed)

        # Load corpus: code first (higher weight), then docs
        parts = []
        for path in ["data/python_code_corpus.txt", "data/programming_reddit.txt"]:
            if Path(path).exists():
                t = Path(path).read_text(encoding="utf-8", errors="replace")
                parts.append(t)
                print(f"  {path}: {len(t):,} chars")
        corpus = "\n\n".join(parts)
        # Repeat code corpus 2x to upweight it
        code = Path("data/python_code_corpus.txt").read_text(encoding="utf-8", errors="replace")
        corpus = code + "\n\n" + corpus
        print(f"  Total (code 2x): {len(corpus):,} chars")

        # Clean: keep printable + newlines + tabs (preserve Python indentation)
        corpus = corpus.replace("\r\n", "\n").replace("\r", "\n")
        corpus = "".join(ch for ch in corpus if ch >= " " or ch in "\n\t")

        # Train BPE on full corpus
        print(f"\nTraining BPE vocab_size={args.vocab_size} …")
        tok = BPETokenizer()
        tok.train(corpus, vocab_size=args.vocab_size)
        print(f"  vocab: {len(tok)}")
        out_dir.mkdir(parents=True, exist_ok=True)
        tok.save(str(out_dir / "tokenizer.json"))

        # Encode in chunks
        print("Encoding …")
        all_ids = []
        chunk = 80_000
        for i in range(0, len(corpus), chunk):
            all_ids.extend(tok.encode(corpus[i:i+chunk], add_special=False))
        print(f"  tokens: {len(all_ids):,}")

        train_ids, val_ids = train_val_split(all_ids, val_frac=0.1)
        train_ds = TokenDataset(train_ids, args.context_len)
        val_ds   = TokenDataset(val_ids,   args.context_len)

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
        n_params = sum(p.size for p in model.parameters())
        print(f"  params: {n_params:,}")
        opt = AdamW(model.parameters(), lr=args.lr)

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
                vl = []
                for _ in range(8):
                    vx, vy = val_ds.random_batch(args.batch, rng)
                    l, _ = GPT.cross_entropy(bwd.forward(vx), vy)
                    vl.append(float(l))
                val_loss = float(np.mean(vl))
                mark = " *" if val_loss < best_val else ""
                elapsed = time.time() - t0
                print(f"  step {step:>5} | train {loss:.4f} | val {val_loss:.4f} | lr {opt.lr:.2e} | {elapsed:.0f}s{mark}")
                if val_loss < best_val:
                    best_val = val_loss
                    save_ckpt(model, cfg, tok, out_dir)

        print(f"\nBest val_loss: {best_val:.4f}  → {out_dir}/")

    # Demo
    prompts = [
        "def fibonacci(n):",
        "def binary_search(arr, target):",
        "class Stack:\n    def __init__(self):",
        "def merge_sort(arr):",
        "# Sort a list of numbers\ndef sort(",
        "def is_palindrome(s):",
        "import os\n\ndef list_files(path):",
        "def gcd(a, b):",
    ]
    print("\n" + "="*60)
    print("Code LLM — Demo")
    print("="*60)
    for prompt in prompts:
        ids = tok.encode(prompt, add_special=False)
        out = model.generate(ids, max_new=80, temperature=0.7)
        print(f"\n>>> {prompt}")
        print(tok.decode(out[len(ids):]))
        print("-"*40)


if __name__ == "__main__":
    main()
