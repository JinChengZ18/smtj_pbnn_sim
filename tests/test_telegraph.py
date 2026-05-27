"""Tests for :mod:`smtj_pbnn_sim.device.telegraph`.

These anchor the stateful telegraph (RTN) model to the same Chapter 2.3
device physics as the rest of the device layer:

* the time-averaged state of a free-running population converges to the
  analytic stationary mean ``tanh(Delta * V / V_c0)``;
* the up-rate is exactly :func:`arrhenius.neel_brown_rate` and the two rates
  balance at zero bias;
* the relaxation (correlation) time peaks at zero bias at the analytic value
  ``tau_0 * exp(Delta) / 2`` and shrinks under drive — the tunable memory.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from smtj_pbnn_sim.device.arrhenius import neel_brown_rate
from smtj_pbnn_sim.device.telegraph import (
    TelegraphParams,
    TelegraphArray,
    up_down_rates,
    stationary_mean,
    relaxation_time,
)

DELTA = 4.91
V_C0 = 0.857
TAU_0 = 1.0e-9


# -----------------------------------------------------------------------------#
# Rates                                                                         #
# -----------------------------------------------------------------------------#

def test_up_rate_matches_neel_brown_rate():
    """r_up must be exactly the Néel-Brown hazard rate used elsewhere."""
    V = np.array([-0.2, 0.0, 0.3])
    r_up, _ = up_down_rates(V, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0)
    assert np.allclose(r_up, neel_brown_rate(V, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0))


def test_rates_balanced_at_zero_bias():
    """At V = 0 the two escape rates are equal (maximum-entropy free running)."""
    r_up, r_dn = up_down_rates(0.0, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0)
    assert abs(float(r_up) - float(r_dn)) < 1e-12


def test_positive_bias_favours_up():
    """Positive bias raises the up-rate above the down-rate."""
    r_up, r_dn = up_down_rates(0.2, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0)
    assert float(r_up) > float(r_dn)


# -----------------------------------------------------------------------------#
# Stationary mean                                                               #
# -----------------------------------------------------------------------------#

def test_stationary_mean_is_tanh():
    """Closed-form stationary mean equals tanh(Delta V / V_c0)."""
    V = np.linspace(-0.3, 0.3, 11)
    assert np.allclose(stationary_mean(V, Delta=DELTA, V_c0=V_C0),
                       np.tanh(DELTA * V / V_C0))


def test_stationary_mean_zero_at_zero_bias():
    assert abs(float(stationary_mean(0.0, Delta=DELTA, V_c0=V_C0))) < 1e-12


def test_empirical_mean_converges_to_stationary():
    """A free-running population's time-average matches the analytic mean."""
    V = 0.05
    arr = TelegraphArray(5000, TelegraphParams(), seed=0)
    dt = 3e-9
    for _ in range(300):                       # burn-in
        arr.step(V, dt)
    samples = np.array([arr.step(V, dt).mean() for _ in range(2000)])
    assert abs(samples.mean() - float(stationary_mean(V))) < 0.02


# -----------------------------------------------------------------------------#
# Relaxation time (the tunable memory)                                          #
# -----------------------------------------------------------------------------#

def test_relaxation_time_zero_bias_value():
    """tau(0) = tau_0 * exp(Delta) / 2."""
    tau0 = float(relaxation_time(0.0, tau_0=TAU_0, Delta=DELTA, V_c0=V_C0))
    assert abs(tau0 - TAU_0 * math.exp(DELTA) / 2.0) < 1e-12


def test_relaxation_time_peaks_at_zero_bias():
    """Memory is longest at zero bias and shrinks under drive (the knob)."""
    taus = [float(relaxation_time(v, Delta=DELTA, V_c0=V_C0))
            for v in (0.0, 0.1, 0.3)]
    assert taus[0] > taus[1] > taus[2]


# -----------------------------------------------------------------------------#
# Stateful array behaviour                                                      #
# -----------------------------------------------------------------------------#

def test_state_is_binary():
    arr = TelegraphArray(256, seed=1)
    s = arr.step(0.1, 2e-9)
    assert set(np.unique(s)).issubset({-1.0, 1.0})


def test_same_seed_same_trajectory():
    a = TelegraphArray(128, seed=7)
    b = TelegraphArray(128, seed=7)
    for _ in range(20):
        assert np.array_equal(a.step(0.05, 2e-9), b.step(0.05, 2e-9))


def test_reset_restores_state():
    arr = TelegraphArray(64, seed=3)
    arr.reset(state=np.ones(64))
    assert np.all(arr.state == 1.0)


def test_heterogeneous_delta_runs():
    """Per-device Delta of correct shape is accepted and steps cleanly."""
    Delta = np.full(50, 4.0)
    arr = TelegraphArray(50, Delta=Delta, V_c0=np.full(50, 0.857), seed=0)
    assert arr.step(0.0, 2e-9).shape == (50,)


# -----------------------------------------------------------------------------#
# Argument validation                                                          #
# -----------------------------------------------------------------------------#

def test_rejects_nonpositive_n():
    with pytest.raises(ValueError):
        TelegraphArray(0)


def test_step_rejects_nonpositive_dt():
    arr = TelegraphArray(8, seed=0)
    with pytest.raises(ValueError):
        arr.step(0.1, 0.0)


def test_rejects_mismatched_delta_shape():
    with pytest.raises(ValueError):
        TelegraphArray(10, Delta=np.full(5, 4.0))
