"""Reservoir-computing performance metrics: NRMSE, linear memory capacity,
and the orthonormalised information processing capacity (Dambre 2012)."""

from __future__ import annotations

from itertools import combinations

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


# ---------------------------------------------------------------------------#
# Information processing capacity (Dambre et al. 2012, Sci. Rep. 2:514)      #
# ---------------------------------------------------------------------------#

def _normalized_legendre(u: np.ndarray, degree: int) -> np.ndarray:
    """Legendre polynomial P_d(u) scaled to unit variance under U(-1, 1).

    The Legendre family is orthogonal w.r.t. the uniform measure on
    [-1, 1] with E[P_d^2] = 1/(2d + 1); multiplying by sqrt(2d + 1)
    makes the basis orthonormal, which is what makes the per-function
    capacities additive.
    """
    coeffs = np.zeros(degree + 1)
    coeffs[degree] = 1.0
    return np.sqrt(2.0 * degree + 1.0) * np.polynomial.legendre.legval(u, coeffs)


def _ipc_basis(max_delay: int, max_degree: int, max_variables: int):
    """Enumerate basis terms: {(delay, degree), ...} with total degree
    <= max_degree over at most ``max_variables`` distinct delays in
    [0, max_delay]."""
    delays = range(max_delay + 1)

    def _compositions(total, parts):
        # orderings of ``total`` into exactly ``parts`` positive integers
        if parts == 1:
            yield (total,)
            return
        for first in range(1, total - parts + 2):
            for rest in _compositions(total - first, parts - 1):
                yield (first,) + rest

    for total_degree in range(1, max_degree + 1):
        for n_vars in range(1, min(total_degree, max_variables) + 1):
            for delay_combo in combinations(delays, n_vars):
                for degree_combo in _compositions(total_degree, n_vars):
                    yield total_degree, tuple(zip(delay_combo, degree_combo))


def information_processing_capacity(
    states: np.ndarray,
    u: np.ndarray,
    *,
    max_delay: int = 20,
    max_degree: int = 3,
    max_variables: int = 3,
    alpha: float = 1.0e-6,
    split: float = 0.5,
    n_shuffles: int = 200,
    seed: int = 0,
) -> dict:
    """Orthonormalised information processing capacity (Dambre 2012).

    Requires ``u`` to be i.i.d. uniform on [-1, 1] (the Legendre basis is
    orthonormal under exactly that input measure).  Every basis function
    is a product of normalized Legendre polynomials of the input at
    distinct delays; its capacity is the held-out r^2 of the optimal
    ridge readout, and orthonormality makes the capacities additive.

    Finite-sample control: capacities are counted only above a noise
    threshold set by the largest capacity obtained on ``n_shuffles``
    time-permuted surrogate targets; the total is also reported against
    the hard upper bound rank(states) (Dambre's theorem).

    Returns a dict with ``total``, ``by_degree`` (dict degree -> summed
    significant capacity), ``threshold``, ``rank_bound``, ``n_basis``,
    ``n_significant``, and ``terms`` (list of (term, degree, capacity)
    for the significant terms, capacity descending).
    """
    states = np.asarray(states, dtype=np.float64)
    u = np.asarray(u, dtype=np.float64)
    if states.shape[0] != u.shape[0]:
        raise ValueError("states and u must share the same length T.")
    if np.abs(u).max() > 1.0 + 1e-9:
        raise ValueError("IPC requires i.i.d. U(-1,1) input.")

    # Common time grid: drop the first max_delay steps so every delayed
    # factor is defined; one SVD of the train states serves every target.
    X = states[max_delay:]
    n = X.shape[0]
    n_tr = int(split * n)
    X_tr, X_te = X[:n_tr], X[n_tr:]
    x_mean = X_tr.mean(axis=0)
    U_svd, S, Vt = np.linalg.svd(X_tr - x_mean, full_matrices=False)
    tol = S.max() * max(X_tr.shape) * np.finfo(float).eps
    rank_bound = int((S > tol).sum())
    # ridge solution in the SVD basis: w = V diag(S/(S^2+alpha)) U^T y
    filt = S / (S ** 2 + alpha)
    Xte_c = X_te - x_mean

    # cache normalized Legendre series per (delay, degree)
    factor_cache: dict[tuple[int, int], np.ndarray] = {}

    def _factor(delay: int, degree: int) -> np.ndarray:
        key = (delay, degree)
        if key not in factor_cache:
            shifted = u[max_delay - delay: len(u) - delay]
            factor_cache[key] = _normalized_legendre(shifted, degree)
        return factor_cache[key]

    def _capacity(target: np.ndarray) -> float:
        y_tr, y_te = target[:n_tr], target[n_tr:]
        y_mean = y_tr.mean()
        w = Vt.T @ (filt * (U_svd.T @ (y_tr - y_mean)))
        pred = Xte_c @ w
        truth = y_te - y_mean
        v_t, v_p = np.var(truth), np.var(pred)
        if v_t == 0.0 or v_p == 0.0:
            return 0.0
        r = np.corrcoef(truth, pred)[0, 1]
        return float(r ** 2)

    # noise floor from time-permuted surrogates (destroys all structure)
    rng = np.random.default_rng(seed)
    probe = _factor(0, 1)
    threshold = max(_capacity(rng.permutation(probe))
                    for _ in range(n_shuffles))

    by_degree: dict[int, float] = {}
    sig_terms = []
    n_basis = 0
    for total_degree, term in _ipc_basis(max_delay, max_degree, max_variables):
        n_basis += 1
        target = np.ones(n)
        for delay, degree in term:
            target = target * _factor(delay, degree)
        c = _capacity(target)
        if c > threshold:
            by_degree[total_degree] = by_degree.get(total_degree, 0.0) + c
            sig_terms.append((term, total_degree, round(c, 4)))
    sig_terms.sort(key=lambda t: -t[2])

    return {
        "total": float(sum(by_degree.values())),
        "by_degree": by_degree,
        "threshold": float(threshold),
        "rank_bound": rank_bound,
        "n_basis": n_basis,
        "n_significant": len(sig_terms),
        "terms": sig_terms,
    }
