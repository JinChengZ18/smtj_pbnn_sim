"""Pin test: the Verilog-A compact model, the Python device layer, and the
committed golden must stay mutually consistent (no silent drift).

Closes the maintainability gap flagged in the EDA audit: gen_golden.py used to
re-implement the sigmoid/tanh/tau formulas, so a change to arrhenius/telegraph
would not propagate to (or break) the golden. This test ties three things
together:

  smtj_sot.va parameter defaults  ->  device/{arrhenius,telegraph}.py formulas
                                  ->  committed eda/testbenches/golden_psw.csv

If any one drifts (a .va parameter edit, a formula change, or a stale committed
golden), this test fails.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
VA = REPO / "eda" / "models" / "smtj_sot.va"
GOLDEN = REPO / "eda" / "testbenches" / "golden_psw.csv"

from smtj_pbnn_sim.device.arrhenius import psw_sigmoid          # noqa: E402
from smtj_pbnn_sim.device.telegraph import (                    # noqa: E402
    stationary_mean,
    relaxation_time,
)


def _va_params() -> dict[str, float]:
    txt = VA.read_text(encoding="utf-8")
    return {m.group(1): float(m.group(2))
            for m in re.finditer(r"parameter\s+real\s+(\w+)\s*=\s*([0-9.eE+-]+)", txt)}


def test_va_params_match_calibration():
    """The .va defaults are the errata-N1 auto-fit operating point."""
    p = _va_params()
    assert abs(p["Vth"] - 0.895783) < 1e-9
    assert abs(p["VT"] - 0.023414) < 1e-9
    assert abs(p["Delta"] - 4.91) < 1e-9
    assert abs(p["Vc0"] - 0.857) < 1e-9
    assert abs(p["tau0"] - 1.0e-9) < 1e-15
    assert abs(p["Rsot"] - 776.0) < 1e-9


def test_va_params_drive_committed_golden():
    """Recomputing the golden from the .va params via the device layer must
    reproduce the committed golden_psw.csv (catches formula or golden drift)."""
    if not GOLDEN.exists():
        pytest.skip("golden_psw.csv not generated")
    p = _va_params()
    g = np.loadtxt(GOLDEN, delimiter=",", skiprows=1)  # cols: V, psw, sinf, tau_ns
    V = g[:, 0]
    psw = np.asarray(psw_sigmoid(V, p["Vth"], p["VT"]))
    sinf = np.asarray(stationary_mean(V, Delta=p["Delta"], V_c0=p["Vc0"]))
    tau_ns = 1.0e9 * np.asarray(relaxation_time(V, tau_0=p["tau0"], Delta=p["Delta"], V_c0=p["Vc0"]))
    assert np.allclose(psw, g[:, 1], atol=1e-12), "psw drift: .va params vs committed golden"
    assert np.allclose(sinf, g[:, 2], atol=1e-12), "sinf drift"
    assert np.allclose(tau_ns, g[:, 3], rtol=1e-9), "tau_ns drift"
