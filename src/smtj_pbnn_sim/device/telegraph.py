"""Stateful random-telegraph-noise (RTN) model of a superparamagnetic sMTJ.

Where :mod:`smtj_pbnn_sim.device.arrhenius` answers *"given a write pulse of
width t_p, what is the probability the cell has switched?"* (a one-shot,
**memoryless** write probability used by the PBNN sampling path), this module
answers *"how does the magnetisation evolve in continuous time under a
sustained bias?"* — i.e. it gives the device a **state with memory**.

That memory is exactly what reservoir computing feeds on, so this is the
device-physics primitive for the sMTJ-reservoir extension. It is deliberately
kept out of the PBNN forward path; nothing in the existing network depends on
it.

Physics
-------
A superparamagnetic junction sits in a double-well energy landscape and hops
between the two states ``s in {-1, +1}`` as a continuous-time two-state Markov
process. A bias voltage tilts the landscape, raising one escape barrier and
lowering the other. Using the same Néel-Brown activation law as the rest of
the device layer, the two escape rates are

    r_up(V)  = (1 / tau_0) * exp[ -Delta * (1 - V / V_c0) ]   # -1 -> +1
    r_dn(V)  = (1 / tau_0) * exp[ -Delta * (1 + V / V_c0) ]   # +1 -> -1

so ``r_up`` is exactly :func:`arrhenius.neel_brown_rate` and ``r_dn`` is the
same with the bias reversed. Two quantities follow in closed form and are the
two knobs reservoir computing cares about:

* **Stationary mean** (the input -> state nonlinearity)

      <s>_inf(V) = (r_up - r_dn) / (r_up + r_dn) = tanh( Delta * V / V_c0 ),

  a sigmoid-shaped transfer with zero-bias slope ``Delta / V_c0``.

* **Relaxation / correlation time** (the fading memory)

      tau(V) = 1 / (r_up + r_dn),

  maximal at ``V = 0`` (tau_max = tau_0 * exp(Delta) / 2, ~tens of ns for the
  Chapter 2.3 device) and shrinking towards ``tau_0`` under strong drive. The
  bias therefore trades **memory** (small |V|, long tau) against
  **nonlinearity** (large |V|, saturated tanh) — the canonical reservoir
  memory/nonlinearity tradeoff, here grounded in device physics.

The per-step update uses the *exact* two-state propagator over an arbitrary
step ``dt`` (no small-dt requirement):

    P(s_{t+dt} = +1 | s_t) = p_inf + (1[s_t=+1] - p_inf) * exp(-dt / tau),

with ``p_inf = r_up / (r_up + r_dn)``.

NumPy-only by design: the evolution is inherently sequential, and keeping it
NumPy lets the reservoir layer and its benchmarks run without torch (matching
experiments 01-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union
import numpy as np

from .arrhenius import neel_brown_rate

ArrayLike = Union[float, np.ndarray]


@dataclass
class TelegraphParams:
    """Néel-Brown parameters for the two-state RTN model.

    Defaults are the Chapter 2.3 Device-A operating point. ``Delta`` and
    ``V_c0`` may also be passed as per-device NumPy arrays to :class:`TelegraphArray`
    for heterogeneous reservoirs.
    """
    tau_0: float = 1.0e-9      # attempt time [s]
    Delta: float = 4.91        # thermal stability factor (dimensionless)
    V_c0: float = 0.857        # zero-thermal critical voltage [V]


def up_down_rates(
    V: ArrayLike,
    *,
    tau_0: float = 1.0e-9,
    Delta: ArrayLike = 4.91,
    V_c0: ArrayLike = 0.857,
) -> tuple[np.ndarray, np.ndarray]:
    """Escape rates ``(r_up, r_dn)`` in [1/s] for bias ``V``.

    ``r_up`` drives ``-1 -> +1`` and is :func:`arrhenius.neel_brown_rate`;
    ``r_dn`` drives ``+1 -> -1`` and is the same law with the bias reversed.
    """
    V = np.asarray(V, dtype=np.float64)
    r_up = neel_brown_rate(V, tau_0=tau_0, Delta=Delta, V_c0=V_c0)
    r_dn = neel_brown_rate(-V, tau_0=tau_0, Delta=Delta, V_c0=V_c0)
    return np.asarray(r_up, dtype=np.float64), np.asarray(r_dn, dtype=np.float64)


def stationary_mean(
    V: ArrayLike,
    *,
    Delta: ArrayLike = 4.91,
    V_c0: ArrayLike = 0.857,
) -> np.ndarray:
    """Time-averaged state ``<s>_inf = tanh(Delta * V / V_c0)`` (in [-1, 1])."""
    V = np.asarray(V, dtype=np.float64)
    return np.tanh(np.asarray(Delta) * V / np.asarray(V_c0))


def relaxation_time(
    V: ArrayLike,
    *,
    tau_0: float = 1.0e-9,
    Delta: ArrayLike = 4.91,
    V_c0: ArrayLike = 0.857,
) -> np.ndarray:
    """Correlation time ``tau(V) = 1 / (r_up + r_dn)`` [s] (the fading memory)."""
    r_up, r_dn = up_down_rates(V, tau_0=tau_0, Delta=Delta, V_c0=V_c0)
    return 1.0 / (r_up + r_dn)


class TelegraphArray:
    """A stateful population of ``n`` two-state superparamagnetic sMTJs.

    Each device is an independent two-state Markov node whose dynamics are set
    by its (optionally per-device) ``Delta`` and ``V_c0``. One :meth:`step`
    advances the whole population by ``dt`` under a per-device bias and returns
    the new ``{-1, +1}`` states. This is the reservoir's pool of dynamical
    nodes.

    Args:
        n: Number of devices.
        params: Nominal :class:`TelegraphParams`.
        Delta: Optional per-device thermal stability (shape ``(n,)``); overrides
            ``params.Delta``. Enables heterogeneous reservoirs.
        V_c0: Optional per-device critical voltage (shape ``(n,)``).
        seed: RNG seed for both the initial state and the stochastic updates.
    """

    def __init__(
        self,
        n: int,
        params: Optional[TelegraphParams] = None,
        *,
        Delta: Optional[np.ndarray] = None,
        V_c0: Optional[np.ndarray] = None,
        seed: Optional[int] = None,
    ):
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        self.n = int(n)
        self.params = params or TelegraphParams()
        self.tau_0 = float(self.params.tau_0)
        self.Delta = (np.full(n, self.params.Delta, dtype=np.float64)
                      if Delta is None else np.asarray(Delta, dtype=np.float64))
        self.V_c0 = (np.full(n, self.params.V_c0, dtype=np.float64)
                     if V_c0 is None else np.asarray(V_c0, dtype=np.float64))
        if self.Delta.shape != (n,) or self.V_c0.shape != (n,):
            raise ValueError("Delta and V_c0 must have shape (n,) when supplied.")
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, state: Optional[np.ndarray] = None) -> None:
        """Reset the population to ``state`` (default: random {-1, +1})."""
        if state is None:
            self.s = self.rng.choice(
                np.array([-1.0, 1.0]), size=self.n).astype(np.float64)
        else:
            self.s = np.asarray(state, dtype=np.float64).copy()

    def step(self, V: ArrayLike, dt: float) -> np.ndarray:
        """Advance all devices by ``dt`` [s] under per-device bias ``V`` [V].

        Uses the exact two-state propagator, so ``dt`` need not be small
        relative to ``tau``. Returns a fresh copy of the new ``{-1, +1}``
        state vector of shape ``(n,)``.
        """
        if dt <= 0:
            raise ValueError(f"dt must be positive, got {dt}")
        V = np.broadcast_to(np.asarray(V, dtype=np.float64), (self.n,))
        r_up, r_dn = up_down_rates(V, tau_0=self.tau_0,
                                   Delta=self.Delta, V_c0=self.V_c0)
        k = r_up + r_dn
        p_inf = r_up / k                       # stationary P(+1)
        decay = np.exp(-k * dt)
        is_plus = self.s > 0.0
        p_plus_next = np.where(is_plus,
                               p_inf + (1.0 - p_inf) * decay,
                               p_inf * (1.0 - decay))
        u = self.rng.random(self.n)
        self.s = np.where(u < p_plus_next, 1.0, -1.0)
        return self.s.copy()

    @property
    def state(self) -> np.ndarray:
        """Current ``{-1, +1}`` state vector (no copy)."""
        return self.s
