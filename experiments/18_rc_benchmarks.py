"""18 -- Benchmark breadth for the sMTJ reservoir.

Mirrors the cross-task validation of the PBNN suite (experiment 10): one fixed
reservoir recipe, several standard reservoir-computing benchmarks, to show the
substrate is a generic temporal processor rather than a single-task construction.

  (a) Mackey-Glass chaotic prediction -- target vs readout trace
  (b) Mackey-Glass NRMSE vs prediction horizon
  (c) information-processing-capacity decomposition (linear / quadratic / cubic),
      mean-field vs real device
  (d) total capacity vs operating-point bias -- linear capacity trades for
      nonlinear capacity, total roughly conserved

Run from the repo root:

    python experiments/18_rc_benchmarks.py
"""

from __future__ import annotations

from pathlib import Path
from itertools import combinations_with_replacement
import sys
import time

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout, nrmse, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402

PURPLE, RED, DEEP, GREEN, LILAC = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4"

MF = dict(n_nodes=120, mode="meanfield", effective_spectral_radius=0.6,
          effective_input_scale=0.8, dt=8e-9, seed=1)
ST = dict(n_nodes=100, mode="stochastic", effective_spectral_radius=0.5,
          effective_input_scale=2.0, dt=25e-9, substeps=25, ensemble=128, seed=1)


def _r2(X, y, *, alpha=1e-4, split=0.6):
    n = X.shape[0]
    n_tr = int(split * n)
    if np.var(y[:n_tr]) < 1e-12:
        return 0.0
    ro = RidgeReadout(alpha=alpha).fit(X[:n_tr], y[:n_tr])
    pred = ro.predict(X[n_tr:])
    truth = y[n_tr:]
    if np.var(truth) < 1e-12 or np.var(pred) < 1e-12:
        return 0.0
    return float(np.corrcoef(truth, pred)[0, 1] ** 2)


def capacities(X, u, *, k_lin=20, k_nl=6):
    """Practical IPC decomposition: summed r^2 by polynomial degree."""
    c1 = sum(_r2(X[k:], u[:-k] if k else u) for k in range(1, k_lin + 1))
    c2 = 0.0
    for k1, k2 in combinations_with_replacement(range(1, k_nl + 1), 2):
        m = max(k1, k2)
        y = np.roll(u, k1)[m:] * np.roll(u, k2)[m:]
        c2 += _r2(X[m:], y)
    c3 = 0.0
    for k1, k2, k3 in combinations_with_replacement(range(1, 4), 3):
        m = max(k1, k2, k3)
        y = np.roll(u, k1)[m:] * np.roll(u, k2)[m:] * np.roll(u, k3)[m:]
        c3 += _r2(X[m:], y)
    return c1, c2, c3


def main() -> None:
    t0 = time.time()

    # (a,b) Mackey-Glass prediction ----------------------------------------#
    mg = tasks.mackey_glass(2600, seed=4)
    mg = (mg - mg.mean()) / mg.std()
    res = SMTJReservoir(ReservoirConfig(**MF), 1)
    horizons = [1, 3, 5, 8, 12]
    mg_nrmse = []
    pred_show = truth_show = None
    for h in horizons:
        X = res.run(mg[:-h], washout=200)
        y = mg[h:][200:]
        n_tr = 1500
        ro = RidgeReadout(alpha=1e-5).fit(X[:n_tr], y[:n_tr])
        p = ro.predict(X[n_tr:])
        mg_nrmse.append(nrmse(y[n_tr:], p))
        if h == 1:
            pred_show, truth_show = p[:200], y[n_tr:][:200]
    print("Mackey-Glass NRMSE by horizon: " +
          ", ".join(f"h={h}:{e:.3f}" for h, e in zip(horizons, mg_nrmse)))

    # (c) capacity decomposition -------------------------------------------#
    u = tasks.memory_capacity_inputs(2200, seed=2)
    Xmf = SMTJReservoir(ReservoirConfig(**MF), 1).run(u, washout=100)
    Xst = SMTJReservoir(ReservoirConfig(**ST), 1).run(u, washout=100)
    c_mf = capacities(Xmf, u[100:])
    c_st = capacities(Xst, u[100:])
    print(f"capacity (linear/quad/cubic) mean-field: {tuple(round(c,2) for c in c_mf)}")
    print(f"capacity (linear/quad/cubic) device    : {tuple(round(c,2) for c in c_st)}")

    # (d) total capacity vs bias -------------------------------------------#
    biases = np.array([0.0, 0.03, 0.06, 0.1, 0.15, 0.22])
    cap_lin, cap_nl = [], []
    for vb in biases:
        cfg = dict(MF); cfg["V_bias"] = float(vb); cfg["effective_input_scale"] = 1.5
        Xb = SMTJReservoir(ReservoirConfig(**cfg), 1).run(u, washout=100)
        c1, c2, c3 = capacities(Xb, u[100:])
        cap_lin.append(c1)
        cap_nl.append(c2 + c3)
    cap_lin = np.array(cap_lin)
    cap_nl = np.array(cap_nl)

    # ----------------------------- figure ---------------------------------#
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    ax[0, 0].plot(truth_show, color="black", lw=1.6, label="target")
    ax[0, 0].plot(pred_show, color=RED, ls="--", lw=1.2, label="readout")
    ax[0, 0].set_xlabel("test step")
    ax[0, 0].set_ylabel("Mackey-Glass (normalised)")
    ax[0, 0].set_title(f"Mackey-Glass 1-step (NRMSE={mg_nrmse[0]:.3f})")
    ax[0, 0].legend(fontsize=10)
    ax[0, 0].grid(alpha=0.3)

    ax[0, 1].plot(horizons, mg_nrmse, "o-", color=PURPLE, lw=2)
    ax[0, 1].set_xlabel("prediction horizon (steps)")
    ax[0, 1].set_ylabel("NRMSE")
    ax[0, 1].set_title("Mackey-Glass vs horizon")
    ax[0, 1].grid(alpha=0.3)

    deg = ["linear\n(C1)", "quadratic\n(C2)", "cubic\n(C3)"]
    xpos = np.arange(3)
    ax[1, 0].bar(xpos - 0.2, c_mf, width=0.4, color=PURPLE, label="mean-field")
    ax[1, 0].bar(xpos + 0.2, c_st, width=0.4, color=LILAC, label="device (ens=128)")
    ax[1, 0].set_xticks(xpos)
    ax[1, 0].set_xticklabels(deg)
    ax[1, 0].set_ylabel("information-processing capacity")
    ax[1, 0].set_title("Capacity by polynomial degree")
    ax[1, 0].legend(fontsize=10)
    ax[1, 0].grid(alpha=0.3, axis="y")

    ax[1, 1].plot(biases * 1e3, cap_lin, "o-", color=DEEP, lw=2, label="linear C1")
    ax[1, 1].plot(biases * 1e3, cap_nl, "s-", color=RED, lw=2, label="nonlinear C2+C3")
    ax[1, 1].plot(biases * 1e3, cap_lin + cap_nl, "^--", color="grey", lw=1.4,
                  label="total")
    ax[1, 1].set_xlabel(r"operating-point bias $V_{bias}$ (mV)")
    ax[1, 1].set_ylabel("capacity")
    ax[1, 1].set_title("Linear capacity trades for nonlinear")
    ax[1, 1].legend(fontsize=9)
    ax[1, 1].grid(alpha=0.3)

    fig.suptitle("sMTJ reservoir: benchmark breadth and processing capacity",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "18_rc_benchmarks.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
