"""Tests for :mod:`smtj_pbnn_sim.ppa`."""

from __future__ import annotations

import math

from smtj_pbnn_sim.ppa import (
    default_28nm, per_mac_energy, layer_inference_energy,
    per_mac_latency, layer_inference_latency,
    tile_area, accelerator_area,
    ReservoirHW, smtj_rc_step_energy, smtj_rc_inference_energy,
    digital_esn_inference_energy,
)


def test_default_tech_returns_TechParams():
    tech = default_28nm()
    assert tech.R_SOT > 0
    assert tech.t_write > 0


def test_smtj_write_energy_property_matches_chapter():
    """SOT write energy from Ohmic dissipation should be ~0.78 pJ at default ops."""
    tech = default_28nm()  # V_wr_nom=0.9 V, R_SOT=776 ohm, t_write=0.75 ns
    assert abs(tech.e_smtj_write - 0.78e-12) / 0.78e-12 < 0.02


def test_per_mac_energy_dominated_by_smtj_write():
    """At the chapter operating point, sMTJ write should dominate per-MAC energy."""
    tech = default_28nm()
    e = per_mac_energy(tech)
    assert tech.e_smtj_write / e > 0.95


def test_layer_energy_scales_linearly_in_T():
    tech = default_28nm()
    e_T1 = layer_inference_energy(256, 256, 1, tech)
    e_T16 = layer_inference_energy(256, 256, 16, tech)
    assert math.isclose(e_T16 / e_T1, 16.0, rel_tol=1e-9)


def test_layer_latency_scales_linearly_in_T():
    tech = default_28nm()
    t_T1 = layer_inference_latency(256, 256, 1, tech)
    t_T8 = layer_inference_latency(256, 256, 8, tech)
    assert math.isclose(t_T8 / t_T1, 8.0, rel_tol=1e-9)


def test_tile_area_breakdown_components():
    tech = default_28nm()
    area = tile_area(256, 256, tech)
    a_array = 256 * 256 * (tech.a_smtj_cell + tech.a_sot_track)
    a_dacs = 256 * tech.a_dac
    a_counters = 256 * tech.a_counter
    assert math.isclose(area, a_array + a_dacs + a_counters, rel_tol=1e-12)


def test_accelerator_scales_with_num_tiles():
    tech = default_28nm()
    a1 = accelerator_area(256, 256, 1, tech)
    a4 = accelerator_area(256, 256, 4, tech)
    assert math.isclose(a4 / a1, 4.0, rel_tol=1e-9)


# -----------------------------------------------------------------------------#
# Reservoir-computing energy model                                              #
# -----------------------------------------------------------------------------#

def test_rc_step_breakdown_components_positive():
    tech = default_28nm()
    bd = smtj_rc_step_energy(ReservoirHW(n_nodes=100, ensemble=96, dt=25e-9), tech)
    assert set(bd) == {"drive", "DAC", "sense", "readout"}
    assert all(v > 0 for v in bd.values())


def test_rc_inference_scales_linearly_in_steps():
    tech = default_28nm()
    hw = ReservoirHW(n_nodes=64, ensemble=32, dt=20e-9)
    e1 = smtj_rc_inference_energy(hw, tech, 100)
    e10 = smtj_rc_inference_energy(hw, tech, 1000)
    assert math.isclose(e10 / e1, 10.0, rel_tol=1e-9)


def test_rc_drive_scales_linearly_in_ensemble():
    """Device-drive energy is O(n_nodes * ensemble): doubling ensemble ~doubles it."""
    tech = default_28nm()
    a = smtj_rc_step_energy(ReservoirHW(n_nodes=50, ensemble=10, dt=20e-9), tech)
    b = smtj_rc_step_energy(ReservoirHW(n_nodes=50, ensemble=20, dt=20e-9), tech)
    assert math.isclose(b["drive"] / a["drive"], 2.0, rel_tol=1e-9)


def test_digital_esn_scales_quadratically_in_N():
    """Dense ESN recurrent cost is O(N^2): 2x nodes ~4x energy at large N."""
    tech = default_28nm()
    e1 = digital_esn_inference_energy(500, tech, 100)
    e2 = digital_esn_inference_energy(1000, tech, 100)
    assert 3.9 < e2 / e1 < 4.0   # ->4 as the N^2 term dominates


def test_cim_lower_bound_cheaper_than_digital_mac():
    tech = default_28nm()
    e_dig = digital_esn_inference_energy(100, tech, 100, digital_mac=True)
    e_cim = digital_esn_inference_energy(100, tech, 100, digital_mac=False)
    assert e_cim < e_dig
