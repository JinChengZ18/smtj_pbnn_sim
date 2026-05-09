"""Tests for :mod:`smtj_pbnn_sim.device.tmr`."""

from __future__ import annotations

import math
import numpy as np
import pytest

from smtj_pbnn_sim.device.tmr import (
    MTJResistance, conductance_from_state, sot_write_energy,
)


def test_tmr_two_state_resistance():
    mtj = MTJResistance(R_P=4.9e3, TMR=1.0)
    assert math.isclose(mtj.R_AP, 9.8e3, rel_tol=1e-9)


def test_conductance_from_state_pm1_mapping():
    mtj = MTJResistance(R_P=4.9e3, TMR=1.0)
    state = np.array([+1.0, -1.0])
    G = conductance_from_state(state, mtj)
    assert math.isclose(float(G[0]), mtj.G_P, rel_tol=1e-9)
    assert math.isclose(float(G[1]), mtj.G_AP, rel_tol=1e-9)


def test_sot_write_energy_chapter_value():
    """E = V^2/R * t  ->  0.78 pJ at 0.9 V, 0.75 ns, 776 ohm (Chapter 2.3)."""
    E = sot_write_energy(V_wr=0.9, t_p=0.75e-9, R_SOT=776.0)
    assert abs(E - 0.78e-12) / 0.78e-12 < 0.02


def test_sot_write_energy_quadratic_in_V():
    """Doubling V should quadruple energy at fixed t_p, R."""
    E1 = sot_write_energy(V_wr=0.5, t_p=1e-9, R_SOT=800.0)
    E2 = sot_write_energy(V_wr=1.0, t_p=1e-9, R_SOT=800.0)
    assert math.isclose(E2 / E1, 4.0, rel_tol=1e-9)
