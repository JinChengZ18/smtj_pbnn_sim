"""Tests for :mod:`smtj_pbnn_sim.reservoir`.

Covers the trained linear readout, the metrics, and the end-to-end property
that the sMTJ reservoir actually possesses fading memory (nonzero memory
capacity). The mean-field mode is used for the memory test so it is fast and
deterministic; the stochastic path is exercised for shape/sanity only.
"""

from __future__ import annotations

import numpy as np
import pytest

from smtj_pbnn_sim.reservoir import (
    ReservoirConfig,
    SMTJReservoir,
    RidgeReadout,
    nrmse,
    memory_capacity,
)
from smtj_pbnn_sim.reservoir import tasks


# -----------------------------------------------------------------------------#
# Ridge readout                                                                 #
# -----------------------------------------------------------------------------#

def test_ridge_recovers_linear_map():
    rng = np.random.default_rng(0)
    X = rng.standard_normal((400, 5))
    W_true = rng.standard_normal((5, 2))
    Y = X @ W_true
    ro = RidgeReadout(alpha=1e-8).fit(X, Y)
    assert np.allclose(ro.predict(X), Y, atol=1e-3)


def test_ridge_predict_before_fit_raises():
    with pytest.raises(RuntimeError):
        RidgeReadout().predict(np.zeros((3, 3)))


def test_ridge_fits_bias_offset():
    rng = np.random.default_rng(1)
    X = rng.standard_normal((200, 3))
    Y = X @ np.array([1.0, -2.0, 0.5]) + 7.0
    ro = RidgeReadout(alpha=1e-8).fit(X, Y)
    assert np.allclose(ro.predict(X), Y, atol=1e-3)


# -----------------------------------------------------------------------------#
# Metrics                                                                       #
# -----------------------------------------------------------------------------#

def test_nrmse_zero_when_perfect():
    y = np.linspace(0, 1, 50)
    assert nrmse(y, y) < 1e-12


def test_nrmse_about_one_for_mean_predictor():
    rng = np.random.default_rng(2)
    y = rng.standard_normal(1000)
    assert abs(nrmse(y, np.full_like(y, y.mean())) - 1.0) < 0.05


def test_memory_capacity_per_delay_bounded():
    rng = np.random.default_rng(3)
    states = rng.standard_normal((600, 10))
    u = rng.uniform(-1, 1, 600)
    mc, per = memory_capacity(states, u, max_delay=15)
    assert per.shape == (15,)
    assert np.all(per >= -1e-9) and np.all(per <= 1.0 + 1e-9)
    assert 0.0 <= mc <= 15.0


# -----------------------------------------------------------------------------#
# End-to-end: the reservoir has fading memory                                   #
# -----------------------------------------------------------------------------#

def test_meanfield_reservoir_has_memory():
    """A mean-field sMTJ reservoir reconstructs several past inputs (MC > 1)."""
    cfg = ReservoirConfig(n_nodes=80, mode="meanfield",
                          effective_spectral_radius=0.6,
                          effective_input_scale=0.5, dt=8e-9, seed=1)
    res = SMTJReservoir(cfg, n_inputs=1)
    u = tasks.memory_capacity_inputs(900, seed=2)
    X = res.run(u, washout=100)
    mc, _ = memory_capacity(X, u[100:], max_delay=20)
    assert mc > 1.0


def test_stochastic_reservoir_runs_and_shapes():
    cfg = ReservoirConfig(n_nodes=20, mode="stochastic", ensemble=8,
                          substeps=5, dt=20e-9, seed=0)
    res = SMTJReservoir(cfg, n_inputs=1)
    X = res.run(np.zeros(200), washout=50)
    assert X.shape == (150, 20)
    assert np.all(np.abs(X) <= 1.0 + 1e-9)


def test_zero_spectral_radius_disables_recurrence():
    cfg = ReservoirConfig(n_nodes=10, mode="meanfield",
                          effective_spectral_radius=0.0, seed=0)
    res = SMTJReservoir(cfg, n_inputs=1)
    assert res.W_res is None


def test_input_channel_mismatch_raises():
    cfg = ReservoirConfig(n_nodes=10, mode="meanfield", seed=0)
    res = SMTJReservoir(cfg, n_inputs=1)
    with pytest.raises(ValueError):
        res.run(np.zeros((100, 3)))


# -----------------------------------------------------------------------------#
# Task generators                                                               #
# -----------------------------------------------------------------------------#

def test_narma10_shape_and_finite():
    u, y = tasks.narma10(500, seed=0)
    assert u.shape == (500,) and y.shape == (500,)
    assert np.all(np.isfinite(y))


def test_memory_capacity_inputs_range():
    u = tasks.memory_capacity_inputs(1000, seed=0)
    assert u.min() >= -1.0 and u.max() <= 1.0
