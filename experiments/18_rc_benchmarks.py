"""18 -- Benchmark breadth for the sMTJ reservoir.

Mirrors the cross-task validation of the PBNN suite (experiment 10): one fixed
reservoir recipe, several standard reservoir-computing benchmarks, to show the
substrate is a generic temporal processor rather than a single-task construction.

  (a) Mackey-Glass chaotic prediction -- target vs readout trace
  (b) Mackey-Glass NRMSE vs prediction horizon
  (c) information-processing-capacity decomposition (linear / quadratic /
      cubic), mean-field vs real device -- orthonormalised Legendre IPC
      (Dambre 2012), shuffle-thresholded, with the rank upper bound printed
  (d) total IPC vs operating-point bias -- how linear capacity trades for
      nonlinear capacity under the canonical measure

Run from the repo root:

    python experiments/18_rc_benchmarks.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout, nrmse, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402
from smtj_pbnn_sim.reservoir.metrics import (                     # noqa: E402
    information_processing_capacity)

PURPLE, RED, DEEP, GREEN, LILAC = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4"

MF = dict(n_nodes=120, mode="meanfield", effective_spectral_radius=0.6,
          effective_input_scale=0.8, dt=8e-9, seed=1)
ST = dict(n_nodes=100, mode="stochastic", effective_spectral_radius=0.5,
          effective_input_scale=2.0, dt=25e-9, substeps=25, ensemble=128, seed=1)


def ipc_by_degree(X, u):
    """Canonical Dambre IPC of states ``X`` driven by i.i.d. U(-1,1) ``u``,
    returned as (C1, C2, C3, rank_bound, threshold)."""
    r = information_processing_capacity(
        X, u, max_delay=20, max_degree=3, max_variables=3, n_shuffles=200)
    bd = r["by_degree"]
    return (bd.get(1, 0.0), bd.get(2, 0.0), bd.get(3, 0.0),
            r["rank_bound"], r["threshold"])


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

    # (c) IPC decomposition --------------------------------------------------#
    # Long i.i.d. U(-1,1) drive: the finite-sample noise floor of the
    # orthonormalised IPC scales down with T, so the mean-field capacities
    # need T ~ 1e4 to resolve degree-3 terms above the shuffle threshold.
    u = tasks.memory_capacity_inputs(12100, seed=2)
    Xmf = SMTJReservoir(ReservoirConfig(**MF), 1).run(u, washout=100)
    Xst = SMTJReservoir(ReservoirConfig(**ST), 1).run(u, washout=100)
    *c_mf, rank_mf, thr_mf = ipc_by_degree(Xmf, u[100:])
    *c_st, rank_st, thr_st = ipc_by_degree(Xst, u[100:])
    print(f"IPC (lin/quad/cubic) mean-field: {tuple(round(c,2) for c in c_mf)} "
          f"total={sum(c_mf):.2f} rank_bound={rank_mf} thr={thr_mf:.4f}")
    print(f"IPC (lin/quad/cubic) device    : {tuple(round(c,2) for c in c_st)} "
          f"total={sum(c_st):.2f} rank_bound={rank_st} thr={thr_st:.4f}")

    # (d) IPC by degree vs bias ----------------------------------------------#
    biases = np.array([0.0, 0.03, 0.06, 0.1, 0.15, 0.22])
    cap_d = {1: [], 2: [], 3: []}
    for vb in biases:
        cfg = dict(MF); cfg["V_bias"] = float(vb); cfg["effective_input_scale"] = 1.5
        Xb = SMTJReservoir(ReservoirConfig(**cfg), 1).run(u, washout=100)
        c1, c2, c3, rank_b, _ = ipc_by_degree(Xb, u[100:])
        cap_d[1].append(c1); cap_d[2].append(c2); cap_d[3].append(c3)
        print(f"  bias {vb*1e3:5.0f} mV: C1={c1:.2f} C2={c2:.2f} C3={c3:.2f} "
              f"total={c1+c2+c3:.2f} rank_bound={rank_b}")
    cap_lin = np.array(cap_d[1])
    cap_quad = np.array(cap_d[2])
    cap_cubic = np.array(cap_d[3])

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
    ax[1, 0].set_ylabel("information processing capacity (Legendre IPC)")
    ax[1, 0].set_title("IPC by polynomial degree")
    ax[1, 0].legend(fontsize=10)
    ax[1, 0].grid(alpha=0.3, axis="y")

    ax[1, 1].plot(biases * 1e3, cap_lin, "o-", color=DEEP, lw=2, label="linear C1")
    ax[1, 1].plot(biases * 1e3, cap_quad, "s-", color=GREEN, lw=2, label="quadratic C2")
    ax[1, 1].plot(biases * 1e3, cap_cubic, "d-", color=RED, lw=2, label="cubic C3")
    ax[1, 1].plot(biases * 1e3, cap_lin + cap_quad + cap_cubic, "^--", color="grey",
                  lw=1.4, label="total (deg<=3)")
    ax[1, 1].set_xlabel(r"operating-point bias $V_{bias}$ (mV)")
    ax[1, 1].set_ylabel("information processing capacity")
    ax[1, 1].set_title("Bias populates the low-degree IPC window")
    ax[1, 1].legend(fontsize=9)
    ax[1, 1].grid(alpha=0.3)

    fig.suptitle("sMTJ reservoir: benchmark breadth and capacity",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "18_rc_benchmarks.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
