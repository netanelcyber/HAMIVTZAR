"""
GPT-style Transformer LLM built from scratch using only NumPy.

Architecture
------------
Embedding → N × (LayerNorm → MultiHeadSelfAttention → LayerNorm → FFN) → LayerNorm → LM Head
Positional encoding: learned.
Attention: causal (autoregressive), scaled dot-product.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class GPTConfig:
    vocab_size: int = 1000
    context_len: int = 128
    n_embed: int = 64
    n_heads: int = 4
    n_layers: int = 2
    ff_mult: int = 4          # hidden dim = n_embed * ff_mult
    dropout: float = 0.1
    seed: int = 42


# ---------------------------------------------------------------------------
# Parameter store (mimics PyTorch Module without the framework)
# ---------------------------------------------------------------------------

class Module:
    """Minimal parameter container."""

    def parameters(self) -> list[np.ndarray]:
        params = []
        for v in vars(self).values():
            if isinstance(v, np.ndarray):
                params.append(v)
            elif isinstance(v, Module):
                params.extend(v.parameters())
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, Module):
                        params.extend(item.parameters())
        return params


# ---------------------------------------------------------------------------
# Layers
# ---------------------------------------------------------------------------

class Embedding(Module):
    def __init__(self, num_embeddings: int, embedding_dim: int, rng: np.random.Generator) -> None:
        self.W = rng.standard_normal((num_embeddings, embedding_dim)).astype(np.float32) * 0.02

    def forward(self, idx: np.ndarray) -> np.ndarray:
        return self.W[idx]


class LayerNorm(Module):
    def __init__(self, dim: int, eps: float = 1e-5) -> None:
        self.gamma = np.ones(dim, dtype=np.float32)
        self.beta = np.zeros(dim, dtype=np.float32)
        self.eps = eps

    def forward(self, x: np.ndarray) -> np.ndarray:
        mean = x.mean(-1, keepdims=True)
        var = ((x - mean) ** 2).mean(-1, keepdims=True)
        return self.gamma * (x - mean) / np.sqrt(var + self.eps) + self.beta


class Linear(Module):
    def __init__(self, in_f: int, out_f: int, rng: np.random.Generator, bias: bool = True) -> None:
        self.W = rng.standard_normal((in_f, out_f)).astype(np.float32) * (0.02 / math.sqrt(in_f))
        self.b: Optional[np.ndarray] = np.zeros(out_f, dtype=np.float32) if bias else None

    def forward(self, x: np.ndarray) -> np.ndarray:
        out = x @ self.W
        if self.b is not None:
            out = out + self.b
        return out

    def parameters(self) -> list[np.ndarray]:
        return [self.W] + ([self.b] if self.b is not None else [])


def gelu(x: np.ndarray) -> np.ndarray:
    return 0.5 * x * (1.0 + np.tanh(math.sqrt(2.0 / math.pi) * (x + 0.044715 * x**3)))


class FeedForward(Module):
    def __init__(self, n_embed: int, ff_mult: int, rng: np.random.Generator) -> None:
        hidden = n_embed * ff_mult
        self.fc1 = Linear(n_embed, hidden, rng)
        self.fc2 = Linear(hidden, n_embed, rng)

    def forward(self, x: np.ndarray) -> np.ndarray:
        return self.fc2.forward(gelu(self.fc1.forward(x)))

    def parameters(self) -> list[np.ndarray]:
        return self.fc1.parameters() + self.fc2.parameters()


class MultiHeadSelfAttention(Module):
    def __init__(self, n_embed: int, n_heads: int, rng: np.random.Generator) -> None:
        assert n_embed % n_heads == 0
        self.n_heads = n_heads
        self.head_dim = n_embed // n_heads
        self.qkv = Linear(n_embed, 3 * n_embed, rng, bias=False)
        self.proj = Linear(n_embed, n_embed, rng)

    def forward(self, x: np.ndarray, mask: np.ndarray) -> np.ndarray:
        B, T, C = x.shape
        qkv = self.qkv.forward(x)                       # (B, T, 3C)
        q, k, v = np.split(qkv, 3, axis=-1)             # each (B, T, C)

        # split into heads
        def split_heads(t: np.ndarray) -> np.ndarray:
            return t.reshape(B, T, self.n_heads, self.head_dim).transpose(0, 2, 1, 3)

        q, k, v = split_heads(q), split_heads(k), split_heads(v)  # (B, H, T, d)

        scale = math.sqrt(self.head_dim)
        attn = (q @ k.transpose(0, 1, 3, 2)) / scale    # (B, H, T, T)
        attn = attn + mask                               # causal mask
        attn = np.exp(attn - attn.max(-1, keepdims=True))
        attn = attn / (attn.sum(-1, keepdims=True) + 1e-9)

        out = attn @ v                                   # (B, H, T, d)
        out = out.transpose(0, 2, 1, 3).reshape(B, T, C)
        return self.proj.forward(out)

    def parameters(self) -> list[np.ndarray]:
        return self.qkv.parameters() + self.proj.parameters()


class TransformerBlock(Module):
    def __init__(self, cfg: GPTConfig, rng: np.random.Generator) -> None:
        self.ln1 = LayerNorm(cfg.n_embed)
        self.attn = MultiHeadSelfAttention(cfg.n_embed, cfg.n_heads, rng)
        self.ln2 = LayerNorm(cfg.n_embed)
        self.ff = FeedForward(cfg.n_embed, cfg.ff_mult, rng)

    def forward(self, x: np.ndarray, mask: np.ndarray) -> np.ndarray:
        x = x + self.attn.forward(self.ln1.forward(x), mask)
        x = x + self.ff.forward(self.ln2.forward(x))
        return x

    def parameters(self) -> list[np.ndarray]:
        return (
            self.ln1.parameters()
            + self.attn.parameters()
            + self.ln2.parameters()
            + self.ff.parameters()
        )


# ---------------------------------------------------------------------------
# Full GPT model
# ---------------------------------------------------------------------------

class GPT(Module):
    def __init__(self, cfg: GPTConfig) -> None:
        self.cfg = cfg
        rng = np.random.default_rng(cfg.seed)
        self.tok_emb = Embedding(cfg.vocab_size, cfg.n_embed, rng)
        self.pos_emb = Embedding(cfg.context_len, cfg.n_embed, rng)
        self.blocks: list[TransformerBlock] = [TransformerBlock(cfg, rng) for _ in range(cfg.n_layers)]
        self.ln_f = LayerNorm(cfg.n_embed)
        self.lm_head = Linear(cfg.n_embed, cfg.vocab_size, rng, bias=False)
        # Build causal mask once
        T = cfg.context_len
        self._causal_mask = np.triu(np.full((T, T), -1e9, dtype=np.float32), k=1)

    def forward(self, idx: np.ndarray) -> np.ndarray:
        """
        idx: (B, T) int32
        returns logits: (B, T, vocab_size)
        """
        B, T = idx.shape
        tok = self.tok_emb.forward(idx)                      # (B, T, C)
        pos = self.pos_emb.forward(np.arange(T))             # (T, C)
        x = tok + pos[None, :, :]
        mask = self._causal_mask[:T, :T][None, None, :, :]  # (1,1,T,T)
        for block in self.blocks:
            x = block.forward(x, mask)
        x = self.ln_f.forward(x)
        return self.lm_head.forward(x)                       # (B, T, V)

    def parameters(self) -> list[np.ndarray]:
        params = (
            self.tok_emb.parameters()
            + self.pos_emb.parameters()
        )
        for b in self.blocks:
            params.extend(b.parameters())
        params.extend(self.ln_f.parameters())
        params.extend(self.lm_head.parameters())
        return params

    # ------------------------------------------------------------------
    # Loss
    # ------------------------------------------------------------------

    @staticmethod
    def cross_entropy(logits: np.ndarray, targets: np.ndarray) -> tuple[float, np.ndarray]:
        """
        logits: (B, T, V)  targets: (B, T)
        Returns (scalar loss, gradient w.r.t. logits same shape)
        """
        B, T, V = logits.shape
        # numerically stable softmax
        lmax = logits.max(-1, keepdims=True)
        exp_l = np.exp(logits - lmax)
        probs = exp_l / exp_l.sum(-1, keepdims=True)

        flat_probs = probs.reshape(B * T, V)
        flat_tgt = targets.reshape(B * T)
        loss = -np.log(flat_probs[np.arange(B * T), flat_tgt] + 1e-9).mean()

        # gradient
        dlogits = flat_probs.copy()
        dlogits[np.arange(B * T), flat_tgt] -= 1.0
        dlogits /= B * T
        return float(loss), dlogits.reshape(B, T, V)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(self, prompt_ids: list[int], max_new: int = 50, temperature: float = 1.0) -> list[int]:
        ctx = list(prompt_ids)
        T = self.cfg.context_len
        for _ in range(max_new):
            window = ctx[-T:]
            idx = np.array([window], dtype=np.int32)
            logits = self.forward(idx)           # (1, t, V)
            last = logits[0, -1, :] / max(temperature, 1e-6)
            last -= last.max()
            probs = np.exp(last)
            probs /= probs.sum()
            next_id = int(np.random.choice(len(probs), p=probs))
            ctx.append(next_id)
        return ctx
