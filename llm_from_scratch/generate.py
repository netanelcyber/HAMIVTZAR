"""
Text generation from a saved checkpoint.

Usage
-----
    python generate.py --prompt "NAME" --tokens 100 --temperature 0.8
"""

import argparse
import json
import dataclasses
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from tokenizer import BPETokenizer
from model import GPT, GPTConfig


def load_checkpoint(out_dir: str) -> tuple[GPT, BPETokenizer]:
    d = Path(out_dir)
    cfg_dict = json.loads((d / "config.json").read_text())
    cfg = GPTConfig(**cfg_dict)
    model = GPT(cfg)
    data = np.load(str(d / "model.npz"))
    params = model.parameters()
    for p, arr in zip(params, data.values()):
        p[:] = arr
    tok = BPETokenizer.load(str(d / "tokenizer.json"))
    return model, tok


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--checkpoint", default="checkpoints")
    p.add_argument("--prompt", default="NAME")
    p.add_argument("--tokens", type=int, default=100)
    p.add_argument("--temperature", type=float, default=0.8)
    args = p.parse_args()

    model, tok = load_checkpoint(args.checkpoint)
    prompt_ids = tok.encode(args.prompt, add_special=False)
    generated = model.generate(prompt_ids, max_new=args.tokens, temperature=args.temperature)
    print(tok.decode(generated))


if __name__ == "__main__":
    main()
