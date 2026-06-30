# LLM From Scratch

GPT-style language model built entirely from scratch using **NumPy only** —
no PyTorch, no TensorFlow, no autograd.  
Trained on **Linux man-page documentation** fetched live from the system.

## Architecture

```
Token Embedding + Positional Embedding
       │
  ┌────┴────────────────────┐  × N layers
  │  LayerNorm              │
  │  Multi-Head Causal Attn │
  │  Residual               │
  │  LayerNorm              │
  │  Feed-Forward (GELU)    │
  │  Residual               │
  └─────────────────────────┘
       │
  LayerNorm  →  LM Head (linear)  →  logits
```

| Component | Detail |
|-----------|--------|
| Tokeniser | Byte Pair Encoding (BPE) trained on corpus |
| Attention | Scaled dot-product, causal mask |
| Activation | GELU |
| Normalisation | Pre-norm LayerNorm |
| Optimiser | AdamW with cosine LR + warmup |
| Backprop | Fully manual — no autograd |

## Files

| File | Purpose |
|------|---------|
| `tokenizer.py` | BPE tokeniser — train, encode, decode, save/load |
| `model.py` | GPT model — forward pass, loss, generation |
| `backprop.py` | Manual backpropagation through every layer |
| `optimizer.py` | AdamW optimiser |
| `data.py` | Linux man-page fetcher + dataset / batch utilities |
| `train.py` | End-to-end training script |
| `generate.py` | Load checkpoint and generate text |

## Quick Start

```bash
# Install the only dependency
pip install numpy

# Train (fetches Linux man pages, saves to ./checkpoints/)
cd llm_from_scratch
python train.py --steps 2000 --vocab-size 1000 --n-embed 64

# Generate from checkpoint
python generate.py --prompt "NAME" --tokens 80 --temperature 0.8
```

## Training options

```
--steps       N        training steps (default 2000)
--batch       N        batch size (default 8)
--lr          F        peak learning rate (default 3e-4)
--vocab-size  N        BPE vocabulary size (default 1000)
--context-len N        sequence length (default 64)
--n-embed     N        embedding / hidden dim (default 64)
--n-heads     N        attention heads (default 4)
--n-layers    N        transformer layers (default 2)
--man-pages   N        how many Linux man pages to fetch (default 30)
--eval-every  N        evaluate on val set every N steps (default 200)
--gen-prompt  TEXT     seed text for end-of-training generation
--out-dir     PATH     where to save checkpoints (default ./checkpoints)
```

## Data Source

The model trains on Linux man pages fetched via the `man` command.  
If `man` is unavailable the script falls back to a small built-in corpus
covering `ls`, `grep`, and `find`.

## Math

**BPE** — iteratively merge the most frequent symbol pair until reaching `vocab_size`.

**Self-attention** — $\text{Attn}(Q,K,V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}} + M\right)V$  
where $M$ is the causal mask ($-\infty$ above the diagonal).

**LayerNorm** — $\hat x = \frac{x - \mu}{\sigma} \cdot \gamma + \beta$

**Loss** — cross-entropy over next-token predictions.

**Backprop** — every gradient is derived analytically in `backprop.py`.
