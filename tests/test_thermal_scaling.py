"""Unit checks for the temperature-scaling chain (T2-2)."""

import numpy as np

from smtj_pbnn_sim.device.thermal_scaling import (
    ThermalStack, bloch, keff_ratio, delta_of_T, vc0_of_T, vth_shift,
    vt_of_T, tmr_of_T,
)

S = ThermalStack()


def test_anchor_identity_at_300K():
    assert np.isclose(bloch(300.0), 1.0)
    assert np.isclose(keff_ratio(300.0), 1.0)
    assert np.isclose(delta_of_T(300.0), S.Delta)
    assert np.isclose(vc0_of_T(300.0), S.V_c0)
    assert np.isclose(vth_shift(300.0), 0.0)
    assert np.isclose(vt_of_T(300.0), S.V_T)
    assert np.isclose(tmr_of_T(300.0), S.TMR)


def test_monotonicity_and_signs():
    T = np.linspace(250.0, 420.0, 35)
    k = keff_ratio(T)
    assert np.all(np.diff(k) < 0), "warming must deepen the compensation"
    assert np.all(np.diff(delta_of_T(T)) < 0)
    assert np.all(np.diff(vt_of_T(T)) > 0), "window broadens with T"
    assert np.all(np.diff(tmr_of_T(T)) < 0)
    assert vth_shift(350.0) < 0 < vth_shift(250.0)


def test_compensation_amplification():
    # K_eff falls FASTER than either constituent term: at +50 K the bare
    # Bloch factor loses ~5%, K_eff loses ~12%.
    f = bloch(350.0)
    assert f > 0.94
    assert keff_ratio(350.0) < f ** 2


def test_athermal_scenario_zeroes_the_shift():
    T = np.array([260.0, 300.0, 380.0])
    assert np.all(vth_shift(T, athermal=True) == 0.0)
