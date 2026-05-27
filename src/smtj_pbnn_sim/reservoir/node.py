"""sMTJ reservoir: a pool of stateful telegraph nodes + input/recurrent drive.

The reservoir maps an input time series ``u[t]`` to a high-dimensional state
trajectory ``X[t, :]`` by driving a population of superparamagnetic sMTJs
(:class:`smtj_pbnn_sim.device.telegraph.TelegraphArray`) and reading their
short-time-averaged magnetisation. Only a linear readout (see
:mod:`smtj_pbnn_sim.reservoir.readout`) is trained; the reservoir itself is
fixed random — the defining property of reservoir computing.

Operating point and the steep transfer
---------------------------------------
The per-node bias voltage at reservoir step ``t`` is

    V_i(t) = V_bias + (W_in @ u[t])_i + (W_res @ x[t-1])_i,

and the node's stationary response is ``tanh(Delta/V_c0 * V)``. The transfer is
**steep**: its zero-bias slope is ``Delta / V_c0 ~ 5.7 /V`` for the Chapter 2.3
device, so a coupling expressed naively in volts produces a much larger
*effective* gain. To keep the reservoir in the echo-state regime we therefore
specify the two couplings in ESN-meaningful **effective** units and convert to
volts internally by dividing by that slope:

    W_in  (volts)  = (effective_input_scale     / slope) * Uniform(-1, 1)
    W_res (volts)  : sparse random, spectral radius = effective_spectral_radius / slope

so ``effective_spectral_radius`` ~ 0.9 behaves like a textbook leaky-ESN.
Setting ``effective_spectral_radius = 0`` gives a bank of independent
stochastic leaky integrators whose memory is purely each device's ``tau(V)``.

Leak and read window
--------------------
Within one reservoir step the bias is held fixed and the array is advanced for
``substeps`` micro-steps of ``dt / substeps``; the node activation is the mean
binary state over those micro-steps. The per-step state retention is
``exp(-dt / tau(V))`` (the leak), so ``dt`` should be a small fraction of the
zero-bias ``tau`` (~68 ns here) to retain several steps of memory.

Stochastic vs mean-field
------------------------
``mode="meanfield"`` evolves the *expected* magnetisation (no sampling) — the
ideal, noise-free reference reservoir, analogous to the PBNN ``software`` mode.
``mode="stochastic"`` samples real telegraph trajectories; each logical node is
backed by an ``ensemble`` of independent devices whose average is the readout,
the hardware-realistic shot-noise reducer (a small sMTJ sub-array per neuron,
integrated by the same counter the PBNN array uses).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional
import numpy as np

from ..device.telegraph import TelegraphParams, TelegraphArray, up_down_rates


@dataclass
class ReservoirConfig:
    """Fixed (untrained) hyper-parameters of an sMTJ reservoir."""
    n_nodes: int = 100
    params: TelegraphParams = field(default_factory=TelegraphParams)

    V_bias: float = 0.0                    # DC operating point [V]
    effective_input_scale: float = 0.6     # ESN-units input gain
    effective_spectral_radius: float = 0.9 # ESN-units recurrent gain (0 disables)

    dt: float = 8.0e-9                     # reservoir step [s]; ~tau/8 at zero bias
    substeps: int = 10                     # telegraph micro-steps per read
    ensemble: int = 24                     # devices averaged per logical node

    delta_cv: float = 0.25                 # per-device Delta spread (D2D variation)
    v_c0_cv: float = 0.0                    # per-device V_c0 spread (D2D variation)
    read_noise: float = 0.0                # additive Gaussian sense noise on the readout
    connectivity: float = 0.2              # recurrent matrix density
    mode: Literal["stochastic", "meanfield"] = "stochastic"
    seed: int = 0


class SMTJReservoir:
    """A fixed random reservoir of superparamagnetic sMTJ nodes."""

    def __init__(self, cfg: ReservoirConfig, n_inputs: int = 1):
        self.cfg = cfg
        self.n_inputs = int(n_inputs)
        rng = np.random.default_rng(cfg.seed)
        N = cfg.n_nodes

        # Steep-transfer slope used to convert ESN-units -> device volts.
        self.slope = cfg.params.Delta / cfg.params.V_c0

        # Per-device heterogeneity (device-to-device variation).
        Delta = np.clip(
            cfg.params.Delta * (1.0 + cfg.delta_cv * rng.standard_normal(N)),
            0.5, None)
        V_c0 = np.clip(
            cfg.params.V_c0 * (1.0 + cfg.v_c0_cv * rng.standard_normal(N)),
            0.05, None)
        self.Delta = Delta
        self.V_c0 = V_c0
        self._noise_rng = np.random.default_rng(cfg.seed + 7)

        # Input weights in volts (one column per input channel).
        self.W_in = (cfg.effective_input_scale / self.slope) * \
            rng.uniform(-1.0, 1.0, size=(N, self.n_inputs))

        # Recurrent matrix in volts, scaled to the requested effective radius.
        if cfg.effective_spectral_radius > 0.0:
            W = rng.standard_normal((N, N))
            W *= (rng.random((N, N)) < cfg.connectivity)
            radius = np.max(np.abs(np.linalg.eigvals(W)))
            if radius > 0:
                W *= (cfg.effective_spectral_radius / self.slope) / radius
            self.W_res = W
        else:
            self.W_res = None

        # Stochastic-mode device pool: ensemble copies per logical node.
        if cfg.mode == "stochastic":
            self.array = TelegraphArray(
                N * cfg.ensemble, cfg.params,
                Delta=np.repeat(Delta, cfg.ensemble),
                V_c0=np.repeat(V_c0, cfg.ensemble),
                seed=cfg.seed + 1)

    # ------------------------------------------------------------------ #
    def _node_voltage(self, u_t: np.ndarray, x_prev: np.ndarray) -> np.ndarray:
        V = self.cfg.V_bias + self.W_in @ u_t
        if self.W_res is not None:
            V = V + self.W_res @ x_prev
        return V

    def _step_meanfield(self, V: np.ndarray, m_prev: np.ndarray) -> np.ndarray:
        r_up, r_dn = up_down_rates(V, tau_0=self.cfg.params.tau_0,
                                   Delta=self.Delta, V_c0=self.V_c0)
        k = r_up + r_dn
        m_inf = (r_up - r_dn) / k
        decay = np.exp(-k * self.cfg.dt)
        return m_inf + (m_prev - m_inf) * decay

    def _step_stochastic(self, V: np.ndarray) -> np.ndarray:
        cfg = self.cfg
        micro_dt = cfg.dt / cfg.substeps
        V_full = np.repeat(V, cfg.ensemble)
        acc = np.zeros(cfg.n_nodes * cfg.ensemble)
        for _ in range(cfg.substeps):
            acc += self.array.step(V_full, micro_dt)
        acc /= cfg.substeps
        return acc.reshape(cfg.n_nodes, cfg.ensemble).mean(axis=1)

    def run(
        self,
        u: np.ndarray,
        *,
        washout: int = 100,
        reset: bool = True,
    ) -> np.ndarray:
        """Drive the reservoir with input ``u`` and return analog states.

        Args:
            u: Input series, shape ``(T,)`` for scalar input or ``(T, n_inputs)``.
            washout: Number of leading steps discarded as transient.
            reset: Re-initialise reservoir state before running.

        Returns:
            State matrix ``X`` of shape ``(T - washout, n_nodes)``, entries in
            ``[-1, 1]``.
        """
        u = np.asarray(u, dtype=np.float64)
        if u.ndim == 1:
            u = u[:, None]
        if u.shape[1] != self.n_inputs:
            raise ValueError(
                f"u has {u.shape[1]} channels, reservoir expects {self.n_inputs}")
        T = u.shape[0]
        if washout >= T:
            raise ValueError(f"washout {washout} >= series length {T}")

        cfg = self.cfg
        x = np.zeros(cfg.n_nodes)
        if reset and cfg.mode == "stochastic":
            self.array.reset()
        states = np.empty((T, cfg.n_nodes), dtype=np.float64)
        for t in range(T):
            V = self._node_voltage(u[t], x)
            x = (self._step_meanfield(V, x) if cfg.mode == "meanfield"
                 else self._step_stochastic(V))
            if cfg.read_noise > 0.0:
                x = np.clip(
                    x + self._noise_rng.normal(0.0, cfg.read_noise, cfg.n_nodes),
                    -1.0, 1.0)
            states[t] = x
        return states[washout:]
