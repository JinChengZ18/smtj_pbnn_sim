"""Néel-Brown / Arrhenius compact models for SOT-MTJ switching probability.

Following the joint write-probability model of Chapter 2.3, three views are
implemented and exposed:

1. Full Néel-Brown (NB) thermal-activation form:

       P_sw(V, t_p) = 1 - exp[ -(t_p / tau_0) * exp( -Delta * (1 - V / V_c0) ) ],

   parameterized by the dimensionless thermal stability factor ``Delta``,
   the zero-thermal critical voltage ``V_c0`` and the attempt time ``tau_0``.
   This is the cross-pulse-width model: it captures V_th(t_w) accurately
   (RMSE < 1 mV across 0.75-100 ns) but UNDERESTIMATES the measured Sigmoid
   slope by a factor of 5-8.

2. Operating-point logistic (Sigmoid) form:

       P_sw(V) = sigmoid( beta_s * (V - V_th) ),  with beta_s = 1 / V_T.

   At a fixed pulse width this is the "operating-point precision model";
   parameters are taken DIRECTLY from measured 100-shot Psw scatter at the
   chosen t_w. For Device A, P->AP, t_w = 0.75 ns (primary reference of
   Chapter 2.3) the values are V_th = 894 mV, beta_s = 44.6 V^-1.

3. NB-with-C2C-narrowing bridge:

       beta_s_predicted = eta_c * beta_s_NB_analytic,

   where eta_c accounts for the physics not contained in the single-domain
   Gumbel distribution of NB (sub-domain co-switching, weak voltage-dependent
   attempt frequency, ...). It is fixed by matching the analytic
   beta_NB = 7.94 V^-1 to the measured operating-point slope beta_s = 44.6 V^-1
   (Chapter 2.3, Device A P->AP, 0.75 ns), giving eta_c = 44.6/7.94 = 5.62.
   This bridge is what allows the Sigmoid model to inherit the V_th(t_w)
   scaling of NB while preserving the measured slope.

All three are NumPy/Torch-array-agnostic: NumPy arrays use ``numpy``
operations, Torch tensors use ``torch``. The dispatch is done by checking
the module of the input. This lets the calibration module run without
torch installed while the network layer can still call the same primitives
on torch tensors.
"""

from __future__ import annotations

import math
from typing import Tuple, Any
import numpy as np


# =============================================================================#
# Backend dispatch                                                              #
# =============================================================================#

def _is_torch(x: Any) -> bool:
    """True if x is a torch tensor (without forcing torch import)."""
    return type(x).__module__.startswith("torch")


def _exp(x):
    if _is_torch(x):
        import torch
        return torch.exp(x)
    return np.exp(x)


def _expm1(x):
    if _is_torch(x):
        import torch
        return torch.expm1(x)
    return np.expm1(x)


def _sigmoid(x):
    if _is_torch(x):
        import torch
        return torch.sigmoid(x)
    return 1.0 / (1.0 + np.exp(-x))


# =============================================================================#
# Full Néel-Brown                                                               #
# =============================================================================#

def psw_neel_brown(
    V,
    t_p: float,
    *,
    tau_0: float = 1e-9,
    Delta: float = 4.91,
    V_c0: float = 0.857,
):
    """Switching probability from the Néel-Brown thermal-activation rate law.

    Args:
        V: Write voltage (volts). NumPy array or Torch tensor.
        t_p: Pulse width (seconds), scalar.
        tau_0: Attempt time (seconds). Default 1 ns (Chapter 2.3 prior).
        Delta: Dimensionless thermal stability factor. Default 4.91
            (Device A, P->AP, Chapter 2.3 NB inversion).
        V_c0: Zero-thermal critical voltage (volts). Default 0.857 V.

    Returns:
        Probabilities in [0, 1], same shape and backend as ``V``.
    """
    if t_p <= 0:
        raise ValueError(f"t_p must be positive, got {t_p}")
    inner = -Delta * (1.0 - V / V_c0)
    rate = (t_p / tau_0) * _exp(inner)
    return -_expm1(-rate)


def neel_brown_rate(
    V,
    *,
    tau_0: float = 1e-9,
    Delta: float = 4.91,
    V_c0: float = 0.857,
):
    """Néel-Brown thermal-activation *hazard rate* (per second).

    This is the instantaneous escape rate that underlies
    :func:`psw_neel_brown` (which integrates it over a pulse as
    ``P_sw = 1 - exp(-rate * t_p)``):

        W(V) = (1 / tau_0) * exp[ -Delta * (1 - V / V_c0) ].

    Exposed separately because the time-domain telegraph model in
    :mod:`smtj_pbnn_sim.device.telegraph` needs the continuous-time rate,
    not a pulse-integrated probability. ``V`` may be a NumPy array or a
    Torch tensor.

    Args:
        V: Bias voltage [V] in the *driven* direction. Backend-agnostic.
        tau_0: Attempt time [s].
        Delta: Dimensionless thermal stability factor.
        V_c0: Zero-thermal critical voltage [V].

    Returns:
        Escape rate [1/s], same shape and backend as ``V``.
    """
    return (1.0 / tau_0) * _exp(-Delta * (1.0 - V / V_c0))


def vth_neel_brown(
    t_p: float,
    *,
    tau_0: float = 1e-9,
    Delta: float = 4.91,
    V_c0: float = 0.857,
) -> float:
    """Half-switch voltage V_th(t_p) from the NB law, P_sw = 1/2.

    Solving the NB expression for P_sw = 0.5 yields the closed form

        V_th(t_p) = V_c0 * (1 - ln(t_p / tau_0 / ln 2) / Delta).
    """
    return V_c0 * (1.0 - math.log(t_p / tau_0 / math.log(2.0)) / Delta)


# =============================================================================#
# Operating-point Sigmoid (logistic) form                                       #
# =============================================================================#

def psw_sigmoid(V, V_th, V_T):
    """Logistic switching probability at a fixed pulse width.

    Args:
        V: Write voltage [V]. NumPy array or Torch tensor.
        V_th: Half-switch voltage [V] (the Sigmoid center). Scalar or array
            broadcastable to ``V``.
        V_T: Slope parameter ``k`` [V]; equals ``1 / beta_s``. Scalar or
            array broadcastable to ``V``.

    Returns:
        Probabilities in (0, 1).
    """
    return _sigmoid((V - V_th) / V_T)


# =============================================================================#
# NB <-> Sigmoid bridge (with C2C narrowing factor)                              #
# =============================================================================#

def sigmoid_params_from_neel_brown(
    *,
    t_p: float,
    tau_0: float = 1e-9,
    Delta: float = 4.91,
    V_c0: float = 0.857,
    eta_c: float = 1.0,
) -> Tuple[float, float]:
    """Analytic Sigmoid (V_th, V_T) from NB parameters with C2C narrowing.

    The half-switch voltage is taken from :func:`vth_neel_brown`. The
    slope of the NB curve at V_th is obtained by differentiating

        P_sw(V) = 1 - exp[ -r(V) ],   r(V) = (t_p/tau_0) exp(-Delta (1 - V/V_c0))

    which gives  dP/dV = (1 - P) * r * Delta / V_c0. Using the half-switch
    condition  r(V_th) = ln 2  to eliminate the t_p dependence,

        dP/dV |_{V = V_th} = (1/2) * ln 2 * Delta / V_c0.

    Matching to the logistic ``P = sigmoid(beta * (V - V_th))`` whose slope
    at V = V_th is beta / 4 yields

        beta_NB_analytic = 2 * ln(2) * (Delta / V_c0).

    For Chapter 2.3 primary parameters Delta = 4.91, V_c0 = 0.857 V this
    gives beta_NB ~ 7.94 V^-1, exactly matching Table 2.3-9. The C2C
    narrowing factor ``eta_c`` is then applied:

        beta_s = eta_c * beta_NB_analytic
        V_T    = 1 / beta_s.

    Args:
        t_p: Pulse width [s] (used only for V_th, not for the slope).
        tau_0: Attempt time [s].
        Delta: Thermal stability factor.
        V_c0: Zero-thermal critical voltage [V].
        eta_c: C2C narrowing factor (>= 1 in practice).

    Returns:
        ``(V_th, V_T)`` in volts.
    """
    if not (t_p > 0 and tau_0 > 0 and Delta > 0 and V_c0 > 0 and eta_c > 0):
        raise ValueError("All NB parameters and eta_c must be positive.")

    V_th = vth_neel_brown(t_p, tau_0=tau_0, Delta=Delta, V_c0=V_c0)
    beta_NB = 2.0 * math.log(2.0) * (Delta / V_c0)
    beta_s = eta_c * beta_NB
    V_T = 1.0 / beta_s
    return V_th, V_T
