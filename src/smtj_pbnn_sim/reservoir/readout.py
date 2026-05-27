"""Linear (ridge) readout — the only trained part of a reservoir computer.

Closed-form ridge regression on the reservoir state features. A bias column is
appended automatically. Kept NumPy-only and dependency-light; this is the
standard RC training step (no backprop, no iteration).
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


def _add_bias(X: np.ndarray) -> np.ndarray:
    return np.hstack([X, np.ones((X.shape[0], 1))])


@dataclass
class RidgeReadout:
    """Closed-form ridge regression ``Y ~ [X | 1] W``.

    Attributes:
        alpha: L2 regularisation strength.
        W: Fitted weight matrix, shape ``(n_features + 1, n_targets)``.
    """
    alpha: float = 1.0e-6
    W: np.ndarray | None = None

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "RidgeReadout":
        """Fit the readout. ``X`` is ``(n, d)``; ``Y`` is ``(n,)`` or ``(n, k)``."""
        Xb = _add_bias(np.asarray(X, dtype=np.float64))
        Y = np.asarray(Y, dtype=np.float64)
        if Y.ndim == 1:
            Y = Y[:, None]
        d = Xb.shape[1]
        # Do not regularise the bias term.
        reg = self.alpha * np.eye(d)
        reg[-1, -1] = 0.0
        self.W = np.linalg.solve(Xb.T @ Xb + reg, Xb.T @ Y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict targets for state features ``X``."""
        if self.W is None:
            raise RuntimeError("RidgeReadout.fit must be called before predict.")
        out = _add_bias(np.asarray(X, dtype=np.float64)) @ self.W
        return out[:, 0] if out.shape[1] == 1 else out
