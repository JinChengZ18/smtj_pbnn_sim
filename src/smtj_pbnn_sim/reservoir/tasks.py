"""Standard reservoir-computing benchmark task generators.

* :func:`narma10` — the NARMA-10 nonlinear autoregressive system; the canonical
  RC benchmark that needs both nonlinearity and ~10 steps of memory.
* :func:`memory_capacity_inputs` — i.i.d. uniform input whose delayed copies are
  the targets for the linear short-term-memory (MC) metric.
* :func:`sine_square` — a sine/square waveform stream for a simple temporal
  classification demo.

All generators return plain NumPy arrays and take an explicit ``seed``.
"""

from __future__ import annotations

import numpy as np


def narma10(n: int, *, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """NARMA-10 input/target pair of length ``n``.

    Input ``u[t] ~ U(0, 0.5)``; target follows

        y[t+1] = 0.3 y[t] + 0.05 y[t] (sum_{i=0}^{9} y[t-i])
                 + 1.5 u[t-9] u[t] + 0.1.

    Returns ``(u, y)`` each of shape ``(n,)``.
    """
    rng = np.random.default_rng(seed)
    u = rng.uniform(0.0, 0.5, size=n)
    y = np.zeros(n)
    for t in range(n - 1):
        window = y[max(0, t - 9):t + 1].sum()
        u_delayed = u[t - 9] if t >= 9 else 0.0
        y[t + 1] = (0.3 * y[t] + 0.05 * y[t] * window
                    + 1.5 * u_delayed * u[t] + 0.1)
    return u, y


def memory_capacity_inputs(n: int, *, seed: int = 0) -> np.ndarray:
    """i.i.d. ``U(-1, 1)`` input series of length ``n`` for the MC metric."""
    rng = np.random.default_rng(seed)
    return rng.uniform(-1.0, 1.0, size=n)


def mackey_glass(n: int, *, tau: int = 17, beta: float = 0.2, gamma: float = 0.1,
                 power: int = 10, dt: float = 1.0, seed: int = 0,
                 discard: int = 1000) -> np.ndarray:
    """Mackey-Glass chaotic time series of length ``n``.

    Integrates dx/dt = beta x(t-tau)/(1 + x(t-tau)^power) - gamma x(t) with a
    simple Euler step and returns ``n`` samples after a transient. ``tau = 17``
    gives the standard mildly-chaotic regime used for RC prediction benchmarks.
    """
    rng = np.random.default_rng(seed)
    tau_steps = int(round(tau / dt))
    total = n + discard
    hist = 1.2 + 0.05 * rng.standard_normal(tau_steps + 1)
    x = list(hist)
    for t in range(tau_steps, tau_steps + total):
        xt, xd = x[t], x[t - tau_steps]
        x.append(xt + dt * (beta * xd / (1.0 + xd ** power) - gamma * xt))
    series = np.asarray(x[tau_steps + discard: tau_steps + discard + n])
    return series


def product_memory(n: int, *, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Nonlinear short-term-memory task: ``y[t] = u[t-1] * u[t-2]``.

    The product of two past inputs cannot be reconstructed by any linear
    function of the input history, so a linear readout succeeds only if the
    reservoir itself supplies the nonlinearity. Paired with the (linear)
    memory-capacity metric it traces the memory/nonlinearity tradeoff.

    Returns ``(u, y)`` each of shape ``(n,)`` with ``u ~ U(-1, 1)``.
    """
    rng = np.random.default_rng(seed)
    u = rng.uniform(-1.0, 1.0, size=n)
    y = np.zeros(n)
    y[2:] = u[1:-1] * u[:-2]
    return u, y


def sine_square(
    n_periods: int, samples_per_period: int = 8, *, seed: int = 0
) -> tuple[np.ndarray, np.ndarray]:
    """Stream of randomly interleaved sine and square periods.

    Returns ``(u, label)`` where ``u`` is the waveform sample stream and
    ``label[t] in {0, 1}`` marks sine (0) vs square (1) for the period that
    sample ``t`` belongs to.
    """
    rng = np.random.default_rng(seed)
    phase = np.linspace(0.0, 2.0 * np.pi, samples_per_period, endpoint=False)
    sine = np.sin(phase)
    square = np.sign(sine + 1e-9)
    u, label = [], []
    for _ in range(n_periods):
        is_square = rng.random() < 0.5
        u.append(square if is_square else sine)
        label.append(np.full(samples_per_period, int(is_square)))
    return np.concatenate(u), np.concatenate(label)
