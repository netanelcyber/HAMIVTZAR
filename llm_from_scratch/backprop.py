"""
Manual backpropagation through the GPT model.

We derive gradients analytically for each layer and propagate
them backwards from the loss through the entire graph.
This avoids autograd frameworks while staying mathematically exact.
"""

import numpy as np
import math
from model import GPT, GPTConfig


def gelu_grad(x: np.ndarray) -> np.ndarray:
    """d/dx GELU(x)"""
    c = math.sqrt(2.0 / math.pi)
    t = np.tanh(c * (x + 0.044715 * x**3))
    dt = 1.0 - t**2
    return 0.5 * (1.0 + t) + 0.5 * x * dt * c * (1.0 + 3 * 0.044715 * x**2)


def layer_norm_backward(
    dout: np.ndarray,
    x: np.ndarray,
    gamma: np.ndarray,
    eps: float = 1e-5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (dx, dgamma, dbeta)."""
    mean = x.mean(-1, keepdims=True)
    var = ((x - mean) ** 2).mean(-1, keepdims=True)
    std_inv = 1.0 / np.sqrt(var + eps)
    xhat = (x - mean) * std_inv
    N = x.shape[-1]
    dgamma = (dout * xhat).sum(tuple(range(x.ndim - 1)))
    dbeta = dout.sum(tuple(range(x.ndim - 1)))
    dxhat = dout * gamma
    dx = std_inv * (
        dxhat - dxhat.mean(-1, keepdims=True) - xhat * (dxhat * xhat).mean(-1, keepdims=True)
    )
    return dx, dgamma, dbeta


def linear_backward(
    dout: np.ndarray,
    x: np.ndarray,
    W: np.ndarray,
    b: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Returns (dx, dW, db)."""
    # dout: (..., out_f), x: (..., in_f), W: (in_f, out_f)
    orig_shape = x.shape
    x_flat = x.reshape(-1, x.shape[-1])
    dout_flat = dout.reshape(-1, dout.shape[-1])
    dW = x_flat.T @ dout_flat
    db = dout_flat.sum(0) if b is not None else None
    dx = (dout_flat @ W.T).reshape(orig_shape)
    return dx, dW, db


class GPTBackward:
    """
    Stores forward-pass activations and computes gradients on demand.
    Call forward() then backward() to get per-parameter gradients.
    """

    def __init__(self, model: GPT) -> None:
        self.model = model
        self.cache: dict = {}

    # ------------------------------------------------------------------
    # Forward (with caching for backward)
    # ------------------------------------------------------------------

    def forward(self, idx: np.ndarray) -> np.ndarray:
        m = self.model
        B, T = idx.shape
        C = m.cfg.n_embed

        tok = m.tok_emb.W[idx]                          # (B,T,C)
        pos_idx = np.arange(T)
        pos = m.pos_emb.W[pos_idx]                      # (T,C)
        x = tok + pos[None]

        self.cache["idx"] = idx
        self.cache["pos_idx"] = pos_idx
        self.cache["x_emb"] = x.copy()

        block_xs = [x]
        block_caches = []
        mask = m._causal_mask[:T, :T][None, None]

        for block in m.blocks:
            bc: dict = {}
            # --- LayerNorm 1 ---
            x_ln1 = block.ln1.forward(x)
            bc["x_pre_ln1"] = x.copy()
            bc["x_ln1"] = x_ln1.copy()

            # --- Attention ---
            qkv = block.attn.qkv.forward(x_ln1)
            bc["x_ln1_for_qkv"] = x_ln1.copy()
            bc["qkv_out"] = qkv.copy()

            q, k, v = np.split(qkv, 3, axis=-1)
            H = block.attn.n_heads
            d = block.attn.head_dim

            def sh(t: np.ndarray) -> np.ndarray:
                return t.reshape(B, T, H, d).transpose(0, 2, 1, 3)

            q_h, k_h, v_h = sh(q), sh(k), sh(v)
            scale = math.sqrt(d)
            scores = (q_h @ k_h.transpose(0, 1, 3, 2)) / scale + mask
            scores_max = scores.max(-1, keepdims=True)
            attn_exp = np.exp(scores - scores_max)
            attn_sum = attn_exp.sum(-1, keepdims=True) + 1e-9
            attn_w = attn_exp / attn_sum                 # (B,H,T,T)
            attn_out = attn_w @ v_h                      # (B,H,T,d)
            attn_out_r = attn_out.transpose(0, 2, 1, 3).reshape(B, T, C)
            attn_proj = block.attn.proj.forward(attn_out_r)
            bc.update({"q_h": q_h, "k_h": k_h, "v_h": v_h,
                        "attn_w": attn_w, "attn_out_r": attn_out_r, "scale": scale})

            x = x + attn_proj
            bc["x_pre_ln2"] = x.copy()

            # --- LayerNorm 2 ---
            x_ln2 = block.ln2.forward(x)
            bc["x_ln2"] = x_ln2.copy()

            # --- FFN ---
            h = block.ff.fc1.forward(x_ln2)
            h_act = gelu(h)
            ffn_out = block.ff.fc2.forward(h_act)
            bc.update({"x_ln2_for_ff": x_ln2.copy(), "ff_h": h.copy(), "ff_h_act": h_act.copy()})

            x = x + ffn_out
            block_xs.append(x.copy())
            block_caches.append(bc)

        self.cache["block_xs"] = block_xs
        self.cache["block_caches"] = block_caches

        x_ln_f = m.ln_f.forward(x)
        self.cache["x_pre_lnf"] = x.copy()
        self.cache["x_ln_f"] = x_ln_f.copy()

        logits = m.lm_head.forward(x_ln_f)
        return logits

    # ------------------------------------------------------------------
    # Backward
    # ------------------------------------------------------------------

    def backward(self, dlogits: np.ndarray) -> list[np.ndarray]:
        """
        dlogits: (B, T, V) — gradient of loss w.r.t. logits.
        Returns list of gradients aligned with model.parameters().
        """
        m = self.model
        B, T = self.cache["idx"].shape
        grads: dict[int, np.ndarray] = {}

        def add_grad(arr: np.ndarray, grad: np.ndarray) -> None:
            key = id(arr)
            if key in grads:
                grads[key] = grads[key] + grad
            else:
                grads[key] = grad.copy()

        # LM head
        x_ln_f = self.cache["x_ln_f"]
        dx, dW_lm, db_lm = linear_backward(dlogits, x_ln_f, m.lm_head.W, m.lm_head.b)
        add_grad(m.lm_head.W, dW_lm)
        if m.lm_head.b is not None:
            add_grad(m.lm_head.b, db_lm)

        # Final layer norm
        dx, dgamma, dbeta = layer_norm_backward(dx, self.cache["x_pre_lnf"], m.ln_f.gamma)
        add_grad(m.ln_f.gamma, dgamma)
        add_grad(m.ln_f.beta, dbeta)

        # Blocks (reverse)
        block_xs = self.cache["block_xs"]
        block_caches = self.cache["block_caches"]
        H_list = [blk.attn.n_heads for blk in m.blocks]
        d_list = [blk.attn.head_dim for blk in m.blocks]

        for layer_i in reversed(range(len(m.blocks))):
            block = m.blocks[layer_i]
            bc = block_caches[layer_i]
            x_in = block_xs[layer_i]
            H = H_list[layer_i]
            d = d_list[layer_i]
            C = m.cfg.n_embed

            # --- FFN backward ---
            dffn_out = dx.copy()
            x_ln2 = bc["x_ln2_for_ff"]
            h_act = bc["ff_h_act"]
            h = bc["ff_h"]

            dx_ln2_fc2, dW_fc2, db_fc2 = linear_backward(dffn_out, h_act, block.ff.fc2.W, block.ff.fc2.b)
            add_grad(block.ff.fc2.W, dW_fc2)
            add_grad(block.ff.fc2.b, db_fc2)

            dh = dx_ln2_fc2 * gelu_grad(h)
            dx_ln2_fc1, dW_fc1, db_fc1 = linear_backward(dh, x_ln2, block.ff.fc1.W, block.ff.fc1.b)
            add_grad(block.ff.fc1.W, dW_fc1)
            add_grad(block.ff.fc1.b, db_fc1)

            dx_ln2, dgamma2, dbeta2 = layer_norm_backward(dx_ln2_fc1, bc["x_pre_ln2"], block.ln2.gamma)
            add_grad(block.ln2.gamma, dgamma2)
            add_grad(block.ln2.beta, dbeta2)

            # residual
            dx = dx + dx_ln2

            # --- Attention backward ---
            x_ln1 = bc["x_ln1_for_qkv"]
            q_h, k_h, v_h = bc["q_h"], bc["k_h"], bc["v_h"]
            attn_w = bc["attn_w"]
            attn_out_r = bc["attn_out_r"]
            scale = bc["scale"]

            dattn_proj, dW_proj, db_proj = linear_backward(dx, attn_out_r, block.attn.proj.W, block.attn.proj.b)
            add_grad(block.attn.proj.W, dW_proj)
            add_grad(block.attn.proj.b, db_proj)

            # reshape to heads
            dattn_out = dattn_proj.reshape(B, T, H, d).transpose(0, 2, 1, 3)  # (B,H,T,d)

            # grad through attn_out = attn_w @ v_h
            dv_h = attn_w.transpose(0, 1, 3, 2) @ dattn_out         # (B,H,T,d)
            dattn_w = dattn_out @ v_h.transpose(0, 1, 3, 2)          # (B,H,T,T)

            # softmax backward
            dscores = attn_w * (dattn_w - (dattn_w * attn_w).sum(-1, keepdims=True))
            dscores = dscores / scale

            dq_h = dscores @ k_h                                     # (B,H,T,d)
            dk_h = dscores.transpose(0, 1, 3, 2) @ q_h

            # merge heads
            def merge(t: np.ndarray) -> np.ndarray:
                return t.transpose(0, 2, 1, 3).reshape(B, T, C)

            dqkv = np.concatenate([merge(dq_h), merge(dk_h), merge(dv_h)], axis=-1)
            dx_ln1_qkv, dW_qkv, _ = linear_backward(dqkv, x_ln1, block.attn.qkv.W, None)
            add_grad(block.attn.qkv.W, dW_qkv)

            dx_ln1, dgamma1, dbeta1 = layer_norm_backward(dx_ln1_qkv, bc["x_pre_ln1"], block.ln1.gamma)
            add_grad(block.ln1.gamma, dgamma1)
            add_grad(block.ln1.beta, dbeta1)

            # residual
            dx = dx + dx_ln1

        # Embeddings
        idx = self.cache["idx"]
        pos_idx = self.cache["pos_idx"]
        dtok = np.zeros_like(m.tok_emb.W)
        np.add.at(dtok, idx, dx)
        add_grad(m.tok_emb.W, dtok)

        dpos = dx.sum(0)
        dpos_emb = np.zeros_like(m.pos_emb.W)
        np.add.at(dpos_emb, pos_idx, dpos)
        add_grad(m.pos_emb.W, dpos_emb)

        # Align with model.parameters()
        params = m.parameters()
        return [grads.get(id(p), np.zeros_like(p)) for p in params]


# convenience re-export
from model import gelu  # noqa: E402, F401
