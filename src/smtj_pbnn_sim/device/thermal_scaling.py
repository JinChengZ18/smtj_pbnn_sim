"""Temperature scaling of the calibrated device interface (T2-2).

Propagates the closed-form magnetic scaling laws already used by the
device platform (Bloch T^3/2 for M_s, modified Callen-Callen with
exponent 2.18 for the interfacial anisotropy K_i, both normalised to
the 300 K calibration anchor) through the near-compensated effective
anisotropy to the quantities the network model consumes:

    K_eff(T) = K_i(T)/t_f - 1/2 mu0 M_s(T)^2 (N_z - N_x)
    E_b(T)   = K_eff(T) V                (retention barrier)
    Delta(T) = Delta_300 * [E_b(T)/E_b(300)] * (300/T)
    V_c0(T)  = V_c0_300 * K_eff(T)/K_eff(300)   (SOT critical voltage
               ~ M_s t_f H_k_eff = 2 K_eff t_f / mu0, R_SOT athermal
               to first order)
    V_th(T)  = anchor + [V_c0(T)(1 - c_p/Delta(T)) - V_c0(1 - c_p/Delta)]
               (Neel-Brown P = 1/2 point SHIFT applied as a common-mode
               offset around the measured 300 K anchor; c_p =
               ln(t_p / (tau_0 ln 2)))
    V_T(T)   = V_T_300 * [V_c0(T)/Delta(T)] / [V_c0/Delta]
               (the measured decision window is C2C-narrowed relative to
               the bare NB slope -- the eta_c gap -- so only the RATIO is
               propagated, keeping the narrowing factor fixed)
    TMR(T)   ~ TMR_300 * bloch(T)^2  (Julliere small-polarisation limit;
               informational, the binary read margin is generous)

Because K_eff is an 81%-compensated difference of two large terms with
different exponents (f^2.18 vs f^2), its temperature slope is amplified
exactly as the Ki-sensitivity analysis found for D2D spread: the
interface term falls FASTER, so warming deepens the compensation.

Scenario band: the full Neel-Brown chain is the PESSIMISTIC end
(thermal-activation picture); the OPTIMISTIC end treats the switching
threshold as athermal (ballistic-regime evidence at sub-ns pulses,
Rehm et al., arXiv:2310.18779) and keeps only the statistical
quantities (Delta, V_T). The 0.75 ns operating pulse sits in the
crossover, so the two ends bracket reality; the single 300 K anchor
plus literature-band framing must be stated wherever these numbers are
used.

Stated assumptions (each moves the V_th slope, none moves V_T):

1. REALIZATION of the superparamagnetic variant. keff_ratio uses the
   as-built memory-grade stack (compensation 0.811). The variant itself
   is not fabricated; the structure analysis offers two routes to
   Delta = 4.91, and the compensation - hence the temperature slope -
   differs strongly between them:
     as_built  c = 0.811  dV_th/dT ~ -2.1 mV/K  (this module's default)
     trim      c = 0.977  ~ -7.0 mV/K  (17% Ki trim, pessimistic)
     shrink    c = 0.726  ~ -1.9 mV/K  (17 nm electrode, mildest)
   Use trim_route()/shrink_route() for the band ends.
2. Callen-Callen exponent n = 2.18 (FMR fit). Literature band
   n in [1.8, 2.8] scales the slope ~0.3x-2.1x; pass cc_exponent to
   ThermalStack for the endpoints.
3. The 52.6 mV offset between the calibrated anchor V_th = 0.8958 and
   the NB-law P = 1/2 point V_c0 (1 - c_p/Delta) = 0.8432 is treated as
   athermal (only the NB shift is propagated).

Identity worth knowing: vt_of_T reduces EXACTLY to V_T * (T/300) -- the
keff_ratio cancels between V_c0(T) and Delta(T) -- so the decision
window (and any slope-only scenario built on it) is independent of the
compensation realization and of n.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MU0 = 4e-7 * np.pi
KB = 1.380649e-23


@dataclass(frozen=True)
class ThermalStack:
    """300 K anchor values of the structural set (Chapter 2 calibration)."""
    T_C: float = 1100.0          # Curie temperature [K]
    T_ref: float = 300.0         # calibration anchor [K]
    cc_exponent: float = 2.18    # Callen-Callen exponent for K_i(T)
    Ki: float = 0.32e-3          # interfacial anisotropy [J/m^2]
    Ms: float = 0.625e6          # saturation magnetisation [A/m]
    tf: float = 1.1e-9           # free-layer thickness [m]
    nz_minus_nx: float = 0.9610  # thin-disc demag difference (65 nm x 1.1 nm,
                                 # vendored ellipsoid model; k_shape/k_int = 0.811)
    # calibrated network-facing anchors (sMTJ variant)
    Delta: float = 4.91
    V_c0: float = 0.857
    V_th: float = 0.895783
    V_T: float = 0.023414
    TMR: float = 1.0
    t_p: float = 0.75e-9
    tau_0: float = 1e-9


def trim_route(**kw) -> ThermalStack:
    """Variant realized by a 17% Ki trim (compensation 0.977)."""
    return ThermalStack(Ki=0.32e-3 * 0.8299, **kw)


def shrink_route(**kw) -> ThermalStack:
    """Variant realized by a 17.2 nm electrode (nz-nx = 0.8606,
    compensation 0.726)."""
    return ThermalStack(nz_minus_nx=0.8606, **kw)


def bloch(T, s: ThermalStack = ThermalStack()):
    """Bloch factor normalised to 1 at T_ref."""
    T = np.asarray(T, dtype=np.float64)
    return (1.0 - (T / s.T_C) ** 1.5) / (1.0 - (s.T_ref / s.T_C) ** 1.5)


def keff_ratio(T, s: ThermalStack = ThermalStack()):
    """K_eff(T) / K_eff(T_ref) through the near-compensated difference."""
    f = bloch(T, s)
    k_int = s.Ki / s.tf
    k_shape = 0.5 * MU0 * s.Ms ** 2 * s.nz_minus_nx
    return (k_int * f ** s.cc_exponent - k_shape * f ** 2) / (k_int - k_shape)


def delta_of_T(T, s: ThermalStack = ThermalStack()):
    """Delta(T) = Delta * [E_b(T)/E_b(ref)] * (T_ref/T)."""
    T = np.asarray(T, dtype=np.float64)
    return s.Delta * keff_ratio(T, s) * (s.T_ref / T)


def vc0_of_T(T, s: ThermalStack = ThermalStack()):
    return s.V_c0 * keff_ratio(T, s)


def vth_shift(T, s: ThermalStack = ThermalStack(), athermal: bool = False):
    """Common-mode V_th(T) - V_th(T_ref) [V]; 0 in the athermal scenario."""
    if athermal:
        return np.zeros_like(np.asarray(T, dtype=np.float64))
    c_p = np.log(s.t_p / (s.tau_0 * np.log(2.0)))
    ref = s.V_c0 * (1.0 - c_p / s.Delta)
    return vc0_of_T(T, s) * (1.0 - c_p / delta_of_T(T, s)) - ref


def vt_of_T(T, s: ThermalStack = ThermalStack()):
    """Decision window V_T(T), keeping the C2C narrowing factor fixed."""
    return s.V_T * (vc0_of_T(T, s) / delta_of_T(T, s)) / (s.V_c0 / s.Delta)


def tmr_of_T(T, s: ThermalStack = ThermalStack()):
    """Julliere small-polarisation limit: TMR ~ P^2 ~ bloch^2."""
    return s.TMR * bloch(T, s) ** 2
