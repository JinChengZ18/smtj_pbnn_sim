"""Tests for :mod:`smtj_pbnn_sim.device.variation`.

The wafer-level statistics produced by the variation sampler must match
the joint model of Chapter 2.3:

    mean(beta_s_per_cell)  ~  eta_c * beta_NB_analytic
    CV(V_T_per_cell)        ~  CV(Delta) / 1   (since beta_NB ~ Delta)

at the PDK baseline CV(Delta) = 7.7 %.
"""

from __future__ import annotations

import math
import numpy as np
import pytest

from smtj_pbnn_sim.device.variation import VariationConfig, VariationSampler


# Primary reference (Chapter 2.3, Device A P->AP).
DELTA = 4.91
V_C0  = 0.857
TAU_0 = 1.0e-9
T_P   = 0.75e-9
ETA_C = 5.34


def test_delta_mode_mean_beta_matches_joint_prediction():
    """20 000-sample mean beta_s should match eta_c * 2 ln(2) * Delta / V_c0."""
    cfg = VariationConfig(mode="delta", cv_delta=0.077, seed=42)
    sampler = VariationSampler(cfg)
    fields = sampler.sample(
        shape=(20_000,),
        V_th_nom=0.894, V_T_nom=1.0 / 44.6,
        R_P_nom=4.9e3, TMR_nom=1.0,
        Delta_nom=DELTA, V_c0_nom=V_C0,
        tau_0=TAU_0, t_p=T_P, eta_c=ETA_C,
    )
    beta_per_cell = 1.0 / fields.V_T
    expected = ETA_C * 2.0 * math.log(2.0) * (DELTA / V_C0)
    # Within 1% of the analytic mean (statistical noise at N=20k).
    assert abs(beta_per_cell.mean() - expected) / expected < 0.01


def test_delta_mode_cv_VT_matches_cv_delta():
    """For beta ~ Delta, CV(V_T = 1/beta) ~ CV(Delta) when CV is small."""
    cv = 0.077
    cfg = VariationConfig(mode="delta", cv_delta=cv, seed=42)
    sampler = VariationSampler(cfg)
    fields = sampler.sample(
        shape=(20_000,),
        V_th_nom=0.894, V_T_nom=1.0 / 44.6,
        R_P_nom=4.9e3, TMR_nom=1.0,
        Delta_nom=DELTA, V_c0_nom=V_C0, eta_c=ETA_C, t_p=T_P,
    )
    cv_VT = fields.V_T.std() / fields.V_T.mean()
    # Delta-method propagation: CV(1/X) = CV(X) for small CV.
    assert abs(cv_VT - cv) / cv < 0.05


def test_delta_mode_requires_NB_params():
    """Without Delta_nom or V_c0_nom, mode='delta' must raise."""
    cfg = VariationConfig(mode="delta", cv_delta=0.05)
    sampler = VariationSampler(cfg)
    with pytest.raises(ValueError):
        sampler.sample(
            shape=(10,),
            V_th_nom=0.9, V_T_nom=0.02, R_P_nom=5e3, TMR_nom=1.0,
        )


def test_sigmoid_direct_mode_keeps_VT_positive():
    """Heavy tails must still leave V_T strictly positive."""
    cfg = VariationConfig(mode="sigmoid_direct",
                          sigma_V_th_rel=0.5, sigma_V_T_rel=0.5, seed=7)
    sampler = VariationSampler(cfg)
    fields = sampler.sample(
        shape=(5_000,),
        V_th_nom=0.894, V_T_nom=0.022,
        R_P_nom=4.9e3, TMR_nom=1.0,
    )
    assert (fields.V_T > 0).all()


def test_seed_reproducibility():
    """Same seed must yield identical fields."""
    kw = dict(shape=(100,), V_th_nom=0.9, V_T_nom=0.02, R_P_nom=5e3,
              TMR_nom=1.0, Delta_nom=5.0, V_c0_nom=0.85, eta_c=5.0)
    a = VariationSampler(VariationConfig(seed=123)).sample(**kw)
    b = VariationSampler(VariationConfig(seed=123)).sample(**kw)
    np.testing.assert_array_equal(a.V_th, b.V_th)
    np.testing.assert_array_equal(a.V_T, b.V_T)
