"""Canonical IPC (Dambre 2012) sanity: exact totals on synthetic systems."""

from __future__ import annotations

import numpy as np
import pytest

from smtj_pbnn_sim.reservoir.metrics import (
    information_processing_capacity,
    _normalized_legendre,
)


@pytest.fixture()
def uniform_input():
    rng = np.random.default_rng(0)
    return rng.uniform(-1.0, 1.0, 6000)


def test_normalized_legendre_orthonormal(uniform_input):
    u = uniform_input
    for d in range(1, 4):
        z = _normalized_legendre(u, d)
        assert abs(z.var() - 1.0) < 0.05          # unit variance
        for d2 in range(1, d):
            z2 = _normalized_legendre(u, d2)
            assert abs(np.mean(z * z2)) < 0.05    # orthogonality


def test_delay_line_ipc_equals_rank(uniform_input):
    """A perfect 5-tap delay line has IPC exactly 5, all linear."""
    u = uniform_input
    X = np.stack([np.roll(u, k) for k in range(5)], axis=1)
    X[:5] = 0.0
    r = information_processing_capacity(
        X, u, max_delay=8, max_degree=2, n_shuffles=100)
    assert r["rank_bound"] == 5
    assert abs(r["total"] - 5.0) < 0.05
    assert abs(r["by_degree"][1] - 5.0) < 0.05
    assert r["by_degree"].get(2, 0.0) < 0.05


def test_squarer_splits_capacity_by_degree(uniform_input):
    """States [u, u^2] carry one linear and one quadratic unit of capacity."""
    u = uniform_input
    X = np.stack([u, u ** 2], axis=1)
    r = information_processing_capacity(
        X, u, max_delay=4, max_degree=3, n_shuffles=100)
    assert abs(r["total"] - 2.0) < 0.05
    assert abs(r["by_degree"][1] - 1.0) < 0.05
    assert abs(r["by_degree"][2] - 1.0) < 0.05
    assert r["total"] <= r["rank_bound"] + 0.05


def test_noise_states_have_no_capacity(uniform_input):
    """States independent of the input stay below the shuffle threshold."""
    u = uniform_input
    rng = np.random.default_rng(1)
    X = rng.normal(size=(len(u), 6))
    r = information_processing_capacity(
        X, u, max_delay=5, max_degree=2, n_shuffles=100)
    assert r["total"] < 0.2
