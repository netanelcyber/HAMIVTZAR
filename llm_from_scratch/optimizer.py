"""
AdamW optimizer — pure NumPy, no framework.
Holds references to parameter arrays and updates them in-place.
"""

import numpy as np
import math


class AdamW:
    def __init__(
        self,
        params: list[np.ndarray],
        lr: float = 3e-4,
        betas: tuple[float, float] = (0.9, 0.999),
        eps: float = 1e-8,
        weight_decay: float = 0.1,
    ) -> None:
        self.params = params
        self.lr = lr
        self.b1, self.b2 = betas
        self.eps = eps
        self.wd = weight_decay
        self.step_n = 0
        self.m = [np.zeros_like(p) for p in params]
        self.v = [np.zeros_like(p) for p in params]

    def step(self, grads: list[np.ndarray]) -> None:
        self.step_n += 1
        t = self.step_n
        bc1 = 1.0 - self.b1 ** t
        bc2 = 1.0 - self.b2 ** t
        for i, (p, g) in enumerate(zip(self.params, grads)):
            self.m[i] = self.b1 * self.m[i] + (1.0 - self.b1) * g
            self.v[i] = self.b2 * self.v[i] + (1.0 - self.b2) * g * g
            m_hat = self.m[i] / bc1
            v_hat = self.v[i] / bc2
            p -= self.lr * (m_hat / (np.sqrt(v_hat) + self.eps) + self.wd * p)

    def zero_grad(self) -> None:
        """Not strictly needed here — grads are passed explicitly."""
        pass
