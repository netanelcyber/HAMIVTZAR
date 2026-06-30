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
| `data.py` | All Linux docs collector (man pages, /usr/share/doc/, info, /etc/) |
| `text_processing.py` | NLTK-based corpus cleaning, sentence splitting, vocab analysis |
| `train.py` | End-to-end training script |
| `generate.py` | Load checkpoint and generate text |

## Quick Start

```bash
# Install dependencies
pip install numpy nltk

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

## Data Sources

All Linux documentation available on the host system is collected automatically:

| Source | Content | ~Size |
|--------|---------|-------|
| `/usr/share/man/man{1,7}` | Command & concept man pages (groff decompressed) | ~2 MB |
| `/usr/share/doc/` | Package READMEs, changelogs, NEWS (695+ packages) | ~8 MB |
| `/usr/share/info/` | GNU info pages (26 files) | ~2 MB |
| `/etc/` | Annotated config files (sshd_config, fstab, sudoers…) | ~50 KB |

Total: **~13 MB → ~6.5M BPE tokens**.

Reddit is not available in this environment (proxy policy).

## NLTK Integration

`text_processing.py` applies NLTK before BPE training:
- **Cleaning**: strip control chars, normalise Unicode, remove troff noise lines
- **Stats**: word count, type/token ratio, top content words (lemmatised)
- NLTK is used for corpus analysis only; the BPE tokeniser is still custom-built from scratch.

## Math

**BPE** — iteratively merge the most frequent symbol pair until reaching `vocab_size`.

**Self-attention** — $\text{Attn}(Q,K,V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}} + M\right)V$  
where $M$ is the causal mask ($-\infty$ above the diagonal).

**LayerNorm** — $\hat x = \frac{x - \mu}{\sigma} \cdot \gamma + \beta$

**Loss** — cross-entropy over next-token predictions.

**Backprop** — every gradient is derived analytically in `backprop.py`.
