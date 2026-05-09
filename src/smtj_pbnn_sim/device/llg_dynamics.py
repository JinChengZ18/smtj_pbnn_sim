"""Macrospin Landau-Lifshitz-Gilbert (LLG) reference solver.

This module is intentionally minimal: it implements the deterministic LLG
equation for a single macrospin under spin-transfer torque, and is used only
to cross-check the Arrhenius-Sigmoid compact model in the device-calibration
notebook. It is NOT called inside the network forward pass; the runtime
sampling path goes through :mod:`smtj_pbnn_sim.device.arrhenius` directly.

For full stochastic LLG (s-LLGS) with thermal Wiener noise and nanosecond
transient simulation, the recommended external tool is the ARM open-source
``mram_simulation_framework`` Python solver. This module provides only the
deterministic skeleton needed for sanity-checking switching thresholds.
"""

from __future__ import annotations

import numpy as np


def llg_step(m: np.ndarray, h_eff: np.ndarray, j_stt: float,
             alpha: float, dt: float) -> np.ndarray:
    """One Heun-type integration step of the macrospin LLG equation.

    Args:
        m: Magnetization unit vector, shape (3,).
        h_eff: Effective field [arbitrary normalized units], shape (3,).
        j_stt: Spin-transfer torque coefficient [normalized current density].
        alpha: Gilbert damping.
        dt: Time step [normalized].

    Returns:
        Updated magnetization unit vector.
    """
    p = np.array([0.0, 0.0, 1.0])  # fixed-layer polarization
    cross_h = np.cross(m, h_eff)
    cross_p = np.cross(m, np.cross(m, p))
    dm = -cross_h - alpha * np.cross(m, cross_h) - j_stt * cross_p
    m_new = m + dm * dt
    return m_new / np.linalg.norm(m_new)
