"""Tests for :mod:`smtj_pbnn_sim.sampling.schedules`."""

from __future__ import annotations

import math

from smtj_pbnn_sim.sampling.schedules import (
    constant_T, layer_depth_T, beta_schedule,
)


def test_constant_T_returns_uniform_list():
    assert constant_T(num_layers=3, T=8) == [8, 8, 8]
    assert constant_T(num_layers=1, T=4) == [4]


def test_layer_depth_T_endpoints():
    """First and last entries must equal T_first and T_last respectively."""
    seq = layer_depth_T(num_layers=5, T_first=4, T_last=32)
    assert seq[0] == 4
    assert seq[-1] == 32
    assert len(seq) == 5


def test_layer_depth_T_monotone_increasing():
    seq = layer_depth_T(num_layers=10, T_first=2, T_last=64)
    for a, b in zip(seq, seq[1:]):
        assert a <= b


def test_layer_depth_T_single_layer_returns_first():
    assert layer_depth_T(num_layers=1, T_first=4, T_last=99) == [4]


def test_beta_schedule_constant_default():
    """Defaults beta_init=beta_final=1 should give beta=1 always."""
    assert math.isclose(beta_schedule(0, 10), 1.0)
    assert math.isclose(beta_schedule(5, 10), 1.0)
    assert math.isclose(beta_schedule(9, 10), 1.0)


def test_beta_schedule_linear_anneal():
    """At epoch=0 should give beta_init; at epoch=total-1 should give beta_final."""
    b0 = beta_schedule(0, 5, beta_init=0.5, beta_final=2.0)
    b_end = beta_schedule(4, 5, beta_init=0.5, beta_final=2.0)
    assert math.isclose(b0, 0.5)
    assert math.isclose(b_end, 2.0)


def test_beta_schedule_total_1_returns_final():
    """Edge case: total_epochs = 1 should return beta_final without div-by-zero."""
    assert math.isclose(beta_schedule(0, 1, beta_init=0.1, beta_final=2.0), 2.0)
