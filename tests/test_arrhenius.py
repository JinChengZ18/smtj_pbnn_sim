"""Tests for :mod:`smtj_pbnn_sim.device.arrhenius`.

These tests anchor the device layer to Chapter 2.3 ground truth:

* analytic V_th(t_w) reproduces the chapter values for Device A AP->P
  to better than 5 mV;
* the analytic NB->Sigmoid bridge gives beta_NB = 2 ln 2 (Delta / V_c0)
  which matches the 7.94 V^-1 reported in Table 2.3-9 to 0.1 V^-1;
* P_sw evaluated at V = V_th equals 0.5 to 6 decimal places;
* numerical derivative of NB matches the analytic slope at V_th.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from smtj_pbnn_sim.device.arrhenius import (
    psw_neel_brown,
    psw_sigmoid,
    vth_neel_brown,
    sigmoid_params_from_neel_brown,
)


# Chapter 2.3 primary reference: Device A, P->AP, t_w = 0.75 ns.
DELTA = 4.91
V_C0  = 0.857
TAU_0 = 1.0e-9
T_P   = 0.75e-9
ETA_C = 5.34


# -----------------------------------------------------------------------------#
# Closed-form V_th                                                              #
# -----------------------------------------------------------------------------#

def test_vth_at_75ns_matches_chapter():
    """Closed-form V_th at 0.75 ns should match the NB inversion in Chapter 2.3.

    Chapter 2.3 Table 2.3-9 reports V_c0 = 857 mV, Delta = 4.91 for
    Device A P->AP. Plugging back gives V_th(0.75 ns) = 843.2 mV.
    """
    V_th = vth_neel_brown(T_P, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0)
    assert abs(V_th - 0.843) < 0.005


def test_vth_monotone_decreasing_in_tp():
    """V_th(t_w) decreases monotonically with t_w (longer pulse needs less V)."""
    tps = [0.5e-9, 1e-9, 5e-9, 50e-9]
    Vths = [vth_neel_brown(tp, Delta=DELTA, V_c0=V_C0) for tp in tps]
    for a, b in zip(Vths, Vths[1:]):
        assert a > b


def test_psw_at_vth_equals_half():
    """P_sw evaluated exactly at V_th should equal 0.5 to high precision."""
    V_th = vth_neel_brown(T_P, Delta=DELTA, V_c0=V_C0)
    P = psw_neel_brown(np.array([V_th]), t_p=T_P, Delta=DELTA, V_c0=V_C0)
    assert abs(float(P[0]) - 0.5) < 1e-6


# -----------------------------------------------------------------------------#
# NB <-> Sigmoid bridge                                                         #
# -----------------------------------------------------------------------------#

def test_analytic_beta_NB_matches_chapter():
    """beta_NB = 2 ln 2 * Delta / V_c0 should give 7.94 V^-1 for primary refs."""
    _, V_T = sigmoid_params_from_neel_brown(
        t_p=T_P, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0, eta_c=1.0,
    )
    beta_NB = 1.0 / V_T
    assert abs(beta_NB - 7.94) < 0.05  # Chapter 2.3 reports 7.94 V^-1


def test_eta_c_scales_beta_linearly():
    """Doubling eta_c should exactly double beta_s."""
    _, V_T_a = sigmoid_params_from_neel_brown(
        t_p=T_P, Delta=DELTA, V_c0=V_C0, eta_c=1.0,
    )
    _, V_T_b = sigmoid_params_from_neel_brown(
        t_p=T_P, Delta=DELTA, V_c0=V_C0, eta_c=2.0,
    )
    assert abs((1.0 / V_T_b) - 2.0 * (1.0 / V_T_a)) < 1e-9


def test_bridge_matches_numerical_NB_slope_at_vth():
    """Analytic beta_NB at V_th should match a numerical derivative of NB."""
    V_th = vth_neel_brown(T_P, Delta=DELTA, V_c0=V_C0)
    # Numerical central difference.
    h = 1e-5
    V = np.array([V_th - h, V_th + h])
    P = psw_neel_brown(V, t_p=T_P, Delta=DELTA, V_c0=V_C0)
    slope_numerical = (P[1] - P[0]) / (2 * h)            # dP/dV at V_th
    # Logistic equivalent: beta_logistic = 4 * dP/dV at V = V_th
    beta_numerical = 4.0 * slope_numerical
    _, V_T = sigmoid_params_from_neel_brown(
        t_p=T_P, Delta=DELTA, V_c0=V_C0, eta_c=1.0,
    )
    beta_analytic = 1.0 / V_T
    assert abs(beta_numerical - beta_analytic) < 0.01


# -----------------------------------------------------------------------------#
# Sigmoid form                                                                  #
# -----------------------------------------------------------------------------#

def test_sigmoid_at_center_is_half():
    P = psw_sigmoid(np.array([0.894]), V_th=0.894, V_T=0.022)
    assert abs(float(P[0]) - 0.5) < 1e-9


def test_sigmoid_monotone_increasing():
    V = np.linspace(0.6, 1.1, 50)
    P = psw_sigmoid(V, V_th=0.894, V_T=0.022)
    assert np.all(np.diff(P) > 0)


# -----------------------------------------------------------------------------#
# Argument validation                                                           #
# -----------------------------------------------------------------------------#

def test_psw_neel_brown_rejects_nonpositive_tp():
    with pytest.raises(ValueError):
        psw_neel_brown(np.array([0.9]), t_p=0.0)


def test_bridge_rejects_zero_eta_c():
    with pytest.raises(ValueError):
        sigmoid_params_from_neel_brown(t_p=T_P, eta_c=0.0)
