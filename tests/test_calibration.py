"""Tests for :mod:`smtj_pbnn_sim.device.calibration`.

These tests load the real measured Chapter 2.3 CSV and assert that the
calibration routines reproduce the published numbers within a tolerance.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from smtj_pbnn_sim.device.calibration import (
    fit_sigmoid_params,
    fit_per_device_direction,
    fit_neel_brown_from_vth_vs_tw,
)


REPO = Path(__file__).resolve().parents[1]
CSV  = REPO / "data" / "smtj_psw_curves" / "measured_0p75ns.csv"


@pytest.fixture(scope="module")
def measured() -> pd.DataFrame:
    if not CSV.exists():
        pytest.skip(f"Measured CSV not found at {CSV}")
    return pd.read_csv(CSV)


# -----------------------------------------------------------------------------#
# Sigmoid fit on real CSV                                                       #
# -----------------------------------------------------------------------------#

def test_primary_reference_matches_chapter(measured: pd.DataFrame):
    """Device A, P->AP, 0.75 ns should fit V_th=894+/-5 mV, beta_s=44+/-3."""
    sub = measured[(measured.device_id == "A")
                   & (measured.direction == "P->AP")]
    sp = fit_sigmoid_params(sub)
    assert abs(sp.V_th - 0.894) < 0.005     # within 5 mV of Chapter 2.3
    assert abs(sp.beta_s - 44.6) < 3.0      # within 3 V^-1
    assert sp.r2 > 0.985                    # Chapter 2.3 reports 0.993


def test_per_group_summary_has_four_rows(measured: pd.DataFrame):
    """Should produce one fit per (device, direction) -- four total."""
    summary = fit_per_device_direction(measured)
    assert len(summary) == 4
    assert set(zip(summary.device_id, summary.direction)) == {
        ("A", "AP->P"), ("A", "P->AP"),
        ("B", "AP->P"), ("B", "P->AP"),
    }


def test_clean_curves_have_high_r2(measured: pd.DataFrame):
    """The two 'clean' P->AP curves should have R^2 > 0.99."""
    summary = fit_per_device_direction(measured)
    clean = summary[summary.direction == "P->AP"]
    assert (clean.r2 > 0.99).all()


# -----------------------------------------------------------------------------#
# Cross-pulse-width NB fit                                                       #
# -----------------------------------------------------------------------------#

def test_nb_fit_recovers_chapter_delta_apto_p():
    """Reconstructed V_th(t_w) regression for Device A AP->P should give
    Delta ~ 5.15 +/- 0.1 and V_c0 ~ 884 +/- 5 mV.
    """
    import numpy as np
    rows = []
    for t_ns in (0.75, 1.0, 2.0, 5.0):
        # Chapter 2.3 Section 2.3.3:  V_AP->P = 0.82 - 0.17 ln(t_w / ns)
        V = 0.82 - 0.17 * np.log(t_ns)
        rows.append({"t_p": t_ns * 1e-9, "V_th": V})
    df = pd.DataFrame(rows)
    nb = fit_neel_brown_from_vth_vs_tw(df, tau_0=1e-9)
    assert abs(nb.Delta - 5.15) < 0.10
    assert abs(nb.V_c0 - 0.884) < 0.005
    assert nb.r2 > 0.999


def test_nb_fit_rejects_too_few_points():
    df = pd.DataFrame({"t_p": [1e-9, 2e-9], "V_th": [0.8, 0.7]})
    with pytest.raises(ValueError):
        fit_neel_brown_from_vth_vs_tw(df)


def test_nb_fit_rejects_positive_slope():
    """If V_th increases with t_w (unphysical), the routine must error."""
    df = pd.DataFrame({"t_p": [1e-9, 2e-9, 5e-9],
                       "V_th": [0.5, 0.6, 0.7]})
    with pytest.raises(ValueError):
        fit_neel_brown_from_vth_vs_tw(df)
