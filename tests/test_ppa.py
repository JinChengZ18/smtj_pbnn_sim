"""Tests for :mod:`smtj_pbnn_sim.ppa`."""

from __future__ import annotations

import math

from smtj_pbnn_sim.ppa import (
    default_28nm, per_mac_energy, layer_inference_energy,
    per_mac_latency, layer_inference_latency,
    tile_area, accelerator_area,
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
