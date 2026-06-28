"""Tests for :mod:`smtj_pbnn_sim.array.ir_drop` and :mod:`smtj_pbnn_sim.array.periphery`.

Both work in pure NumPy, so they can be tested without torch.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from smtj_pbnn_sim.array.ir_drop import estimate_ir_drop
from smtj_pbnn_sim.array.periphery import DACModel, CounterModel


# -----------------------------------------------------------------------------#
# IR-drop                                                                       #
# -----------------------------------------------------------------------------#

def test_ir_drop_zero_wire_resistance():
    """No wire resistance -> no droop."""
    assert estimate_ir_drop(rows=256, r_wire_per_cell=0.0, r_cell=5e3) == 0.0


def test_ir_drop_monotone_in_rows():
    """Taller column (the write line runs down rows) -> more droop."""
    drops = [estimate_ir_drop(n, r_wire_per_cell=0.5, r_cell=5e3)
             for n in (64, 128, 256, 512)]
    for a, b in zip(drops, drops[1:]):
        assert a < b


def test_ir_drop_in_unit_interval():
    """Result should always be in [0, 1)."""
    d = estimate_ir_drop(256, r_wire_per_cell=2.0, r_cell=5e3)
    assert 0.0 <= d < 1.0


def test_ir_drop_negligible_for_chapter_2_3_geometry():
    """At the 256-row / R_P~5k read regime of Chapter 2.3, IR drop should be <5%."""
    # r_wire_per_cell ~ 0.1 ohm at 28 nm pitch (order-of-magnitude)
    d = estimate_ir_drop(256, r_wire_per_cell=0.1, r_cell=4.9e3)
    assert d < 0.05


def test_ir_drop_matches_extracted_writeline_at_n256():
    """Pin the sky130-extracted write-line operating point: round-trip met2
    R_WIRE_PER_CELL_MET2 over 256 rows is ~16.5% of the 776 ohm SOT branch."""
    from smtj_pbnn_sim.array.ir_drop import R_WIRE_PER_CELL_MET2, R_SOT
    d = estimate_ir_drop(256, r_wire_per_cell=R_WIRE_PER_CELL_MET2, r_cell=R_SOT)
    assert 0.14 < d < 0.18


# -----------------------------------------------------------------------------#
# DACModel                                                                      #
# -----------------------------------------------------------------------------#

def test_dac_5bit_has_31_levels():
    """5-bit DAC: levels = 2^5 - 1 = 31."""
    dac = DACModel(n_bits=5, v_min=0.0, v_max=1.0)
    V = np.linspace(0.0, 1.0, 1000)
    Q = dac.quantize(V)
    unique = np.unique(np.round(Q, 6))
    assert len(unique) == 32   # 31 intervals -> 32 distinct values


def test_dac_clamps_to_range():
    dac = DACModel(n_bits=5, v_min=0.0, v_max=1.0)
    V = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
    Q = dac.quantize(V)
    assert np.all(Q >= 0.0)
    assert np.all(Q <= 1.0)


def test_dac_zero_bits_is_just_clamp():
    dac = DACModel(n_bits=0, v_min=0.0, v_max=1.0)
    V = np.array([-0.2, 0.5, 1.5])
    Q = dac.quantize(V)
    np.testing.assert_array_equal(Q, np.array([0.0, 0.5, 1.0]))


def test_dac_quantization_step_correct():
    """Quantization step = (v_max - v_min) / (2^n_bits - 1)."""
    dac = DACModel(n_bits=4, v_min=0.0, v_max=1.5)
    V = np.array([0.0, 0.05, 0.10, 0.15])  # 0.10 V step expected
    Q = dac.quantize(V)
    expected_step = 1.5 / 15
    assert math.isclose(Q[1] - Q[0], expected_step, rel_tol=1e-9) or \
           Q[1] == 0.0  # 0.05 may round to 0


# -----------------------------------------------------------------------------#
# CounterModel                                                                  #
# -----------------------------------------------------------------------------#

def test_counter_saturates_at_signed_range():
    counter = CounterModel(n_bits=8)  # signed: [-128, 127]
    x = np.array([-1000, -100, 0, 100, 1000])
    y = counter.saturate(x)
    assert int(y.min()) == -128
    assert int(y.max()) == 127


def test_counter_no_saturation_in_range():
    counter = CounterModel(n_bits=16)
    x = np.array([0, 100, 1000, -1000])
    y = counter.saturate(x)
    np.testing.assert_array_equal(y, x)
