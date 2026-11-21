"""Online pairwise logistic preference model with a diagonal Laplace posterior (for Thompson sampling)."""
import numpy as np

from .features import DIM


def _sig(z):
    return 1 / (1 + np.exp(-z))


class PreferenceLearner:
    def __init__(self, dim=DIM, lr=1.0, l2=0.005, var0=1.0):
        self.lr, self.l2 = lr, l2
        self.w = np.zeros(dim)
        self.prec = np.ones(dim) / var0
        self.n = 0

    def score(self, x) -> float:
        """Centered preference in (-0.5, 0.5). Zero for a fresh model, so day one is rules-driven."""
        return float(_sig(self.w @ np.asarray(x)) - 0.5)

    def update(self, chosen, rejected) -> None:
        c = np.asarray(chosen)
        for r in rejected:
            d = c - np.asarray(r)
            for sign, label in ((1, 1), (-1, 0)):  # two training pairs per rejected look
                dd = sign * d
                p = _sig(self.w @ dd)
                self.w += self.lr * (label - p) * dd - self.l2 * self.w
                self.prec += p * (1 - p) * dd * dd
        self.n += 1

    def sample(self, rng) -> np.ndarray:
        return self.w + rng.normal(size=self.w.shape) / np.sqrt(self.prec)

    def score_with(self, w, x) -> float:
        return float(_sig(w @ np.asarray(x)) - 0.5)

    def to_json(self) -> dict:
        return {"w": self.w.tolist(), "prec": self.prec.tolist(), "n": self.n}

    @classmethod
    def from_json(cls, d):
        m = cls()
        if d and len(d["w"]) == len(m.w):
            m.w, m.prec, m.n = np.array(d["w"]), np.array(d["prec"]), d["n"]
        return m
