"""Reservoir-computing performance metrics: NRMSE and linear memory capacity."""

from __future__ import annotations

import numpy as np

from .readout import RidgeReadout


def nrmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Normalised RMSE: ``sqrt(MSE / var(y_true))``. 0 is perfect, 1 ~ chance."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    var = np.var(y_true)
    if var == 0.0:
        return float("nan")
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2) / var))


def _forgetting_curve_point(
    states: np.ndarray, u: np.ndarray, k: int, *, alpha: float, split: float
) -> float:
    """Coefficient of determination ``r^2`` for reconstructing ``u[t-k]``.

    Trains a ridge readout on the first ``split`` fraction of the (aligned)
    data and evaluates the squared correlation on the held-out tail.
    """
    if k == 0:
        target = u
        X = states
    else:
        target = u[:-k]
        X = states[k:]
    n = X.shape[0]
    n_tr = int(split * n)
    ro = RidgeReadout(alpha=alpha).fit(X[:n_tr], target[:n_tr])
    pred = ro.predict(X[n_tr:])
    truth = target[n_tr:]
    if np.var(truth) == 0.0 or np.var(pred) == 0.0:
        return 0.0
    r = np.corrcoef(truth, pred)[0, 1]
    return float(r ** 2)


def memory_capacity(
    states: np.ndarray,
    u: np.ndarray,
    *,
    max_delay: int = 30,
    alpha: float = 1.0e-6,
    split: float = 0.5,
) -> tuple[float, np.ndarray]:
    """Linear short-term memory capacity (Jaeger 2001).

    For each delay ``k = 1..max_delay`` the optimal linear readout reconstructs
    ``u[t-k]`` from the reservoir state ``states[t]``; the per-delay capacity is
    the squared correlation ``r^2`` and the total capacity is their sum,
    bounded above by the number of linearly independent reservoir features.

    Args:
        states: Reservoir state matrix ``(T, n_nodes)``.
        u: The driving input series aligned with ``states`` (length ``T``).
        max_delay: Largest delay evaluated.
        alpha: Ridge regularisation for each delay readout.
        split: Train fraction; the rest is held out for the ``r^2`` estimate.

    Returns:
        ``(mc_total, mc_per_delay)`` where ``mc_per_delay[k-1]`` is the capacity
        at delay ``k``.
    """
    states = np.asarray(states, dtype=np.float64)
    u = np.asarray(u, dtype=np.float64)
    if states.shape[0] != u.shape[0]:
        raise ValueError("states and u must share the same length T.")
    per_delay = np.array([
        _forgetting_curve_point(states, u, k, alpha=alpha, split=split)
        for k in range(1, max_delay + 1)
    ])
    return float(per_delay.sum()), per_delay
