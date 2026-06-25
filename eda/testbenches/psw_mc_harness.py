#!/usr/bin/env python3
"""P1/P2 stochastic-write harness: harness-owned RNG reproduces the Bernoulli p-bit.

OpenVAF cannot do reliable in-.va randomness, so the open-source path keeps the
RNG in the HARNESS: per trial it evaluates the device switching probability
P_sw(V_wr) and draws a seeded uniform to decide the flip (event-driven Bernoulli).
This script:
  * reproduces the calibrated sigmoid via Monte-Carlo (the p-bit premise),
  * integrates the Ohmic SOT write energy per write,
  * is structured so eval_psw() can later evaluate smtj_sot.va through ngspice
    instead of the inline formula (one-function swap; backend='ngspice' stub).

Runs now with pure Python (no EDA tools). Seed is logged for reproducibility
(addresses the research's #1 risk: stochastic-switching reproducibility).

Run:  python eda/testbenches/psw_mc_harness.py [--n 2000] [--seed 20260626]
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np

# calibrated params (must match eda/models/smtj_sot.va defaults)
VTH, VT = 0.895783, 0.023414
RSOT, TW, VWR = 776.0, 0.75e-9, 0.90
HERE = Path(__file__).resolve().parent


def eval_psw_analytic(V):
    return 1.0 / (1.0 + np.exp(-(V - VTH) / VT))


def eval_psw(V, backend="analytic"):
    """Switching probability at write voltage V. Swap backend to 'ngspice' later."""
    if backend == "analytic":
        return eval_psw_analytic(V)
    if backend == "ngspice":
        raise NotImplementedError(
            "ngspice point-eval of smtj_sot.va — wire in after install "
            "(reuse the OSDI load + op() from run_regression.py).")
    raise ValueError(backend)


def mc_psw(Vs, n_trials, seed, backend="analytic"):
    """Harness-owned, seeded Bernoulli draws -> empirical P_sw(V)."""
    rng = np.random.default_rng(seed)
    out = []
    for V in Vs:
        p = float(eval_psw(V, backend))
        u = rng.random(n_trials)               # one draw per write trial
        out.append(int(np.sum(u < p)) / n_trials)
    return np.array(out)


def write_energy_J(V=VWR):
    return V * V / RSOT * TW                    # Ohmic SOT write energy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20260626)
    ap.add_argument("--backend", default="analytic")
    a = ap.parse_args()

    Vs = np.round(np.arange(0.84, 0.951, 0.01), 3)
    p_an = eval_psw_analytic(Vs)
    p_mc = mc_psw(Vs, a.n, a.seed, a.backend)
    err = np.abs(p_mc - p_an)
    sigma = float(np.sqrt(0.25 / a.n))         # worst-case binomial 1-sigma at p=0.5

    summary = {
        "seed": a.seed, "n_trials": a.n, "backend": a.backend,
        "max_abs_err_vs_analytic": float(err.max()),
        "binomial_1sigma": sigma,
        "pass_within_4sigma": bool(err.max() < 4 * sigma),
        "write_energy_pJ": write_energy_J() * 1e12,
    }
    print("V      P_sw(analytic)  P_sw(MC)   |err|")
    for V, an, m, e in zip(Vs, p_an, p_mc, err):
        print(f"{V:.3f}     {an:.4f}        {m:.4f}    {e:.4f}")
    print(json.dumps(summary, indent=2))
    (HERE / "mc_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
