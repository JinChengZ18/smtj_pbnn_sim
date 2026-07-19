#!/usr/bin/env python3
"""Column-height scan of read-path IR compression (reconciles 4.3 vs 4.6).

Section 4.3 keeps the behavioral IR model off by default below 256x256 on
the argument that the digital threshold absorbs the read-path drop, while
the Section 4.6 replay of a single N = 64 column measures a 0.69 analog
slope and 86% raw decision agreement. This scan runs the SAME exact
nodal solver that reproduced ngspice to sub-uV at N = 64
(``nodal_solve_check.py``) across N in {16, 32, 64, 128, 256} and reports,
per column height:

  * the analog popcount slope (ladder compression),
  * the mean far-end IR drop,
  * raw decision agreement against the ideal comparator, and
  * agreement after a one-point slope recalibration (the "threshold
    absorbs it" mechanism made explicit).

The boundary where UNCOMPENSATED absorption stops holding is the number
both sections must quote.

Run (Windows or WSL): python eda/hero/nodal_ir_scaling.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

RP, TMR, VR = 4900.0, 1.0, 0.1
GP, GAP = 1.0 / RP, 1.0 / (RP * (1.0 + TMR))
LSB_I = (VR / 2.0) * (GP - GAP)
R_SEG = 0.125 / 0.23 * 2.0
R_TAP = 1e-3
VCM = 0.9
GAIN = 2e4
SEED = 20260713
N_TRIALS = 600
NS = (16, 32, 64, 128, 256)


def solve_line(N, gcell, i_inject, r_ti):
    Vdrv = VCM + VR / 2.0
    g_cell_eff = 1.0 / (1.0 / gcell + R_TAP)
    gseg = 1.0 / R_SEG
    gti = 1.0 / r_ti
    A = np.zeros((N + 1, N + 1))
    b = np.zeros(N + 1)
    for i in range(N):
        A[i, i] += g_cell_eff[i]
        b[i] += g_cell_eff[i] * Vdrv
        if i < N - 1:
            A[i, i] += gseg
            A[i, i + 1] -= gseg
            A[i + 1, i + 1] += gseg
            A[i + 1, i] -= gseg
    A[N - 1, N - 1] += gti
    A[N - 1, N] -= gti
    A[N, N] += gti
    A[N, N - 1] -= gti
    b[N - 1] -= i_inject
    A[N, :] = 0.0
    A[N, N] = 1.0
    A[N, N - 1] = GAIN
    b[N] = VCM * (1.0 + GAIN)
    v = np.linalg.solve(A, b)
    return float(v[N]), float(v[N - 1]), float(v[0])


def scan(N: int) -> dict:
    rng = np.random.default_rng(SEED + N)
    r_ti = 0.6 / (2.0 * 3.0 * np.sqrt(N) * LSB_I)   # slope-matched budget
    i_cm = N * (GP + GAP) / 2.0 * (VR / 2.0)
    p = rng.uniform(0.1, 0.9, N)
    mu_pc = float(np.sum(2 * p - 1))
    theta = 2 * int(round(mu_pc / 2.0))
    i_th = (theta + 1) * LSB_I / 2.0

    vpre, pcs, vfar = [], [], []
    states = np.where(rng.random((N_TRIALS, N)) < p[None, :], 1, -1)
    for srow in states:
        gp_line = np.where(srow > 0, GP, GAP)
        gn_line = np.where(srow > 0, GAP, GP)
        vop, vgp, v0p = solve_line(N, gp_line, i_cm + i_th, r_ti)
        von, _, _ = solve_line(N, gn_line, i_cm - i_th, r_ti)
        vpre.append(vop - von)
        vfar.append(v0p - vgp)
        pcs.append(int(srow.sum()))
    vpre = np.array(vpre); pcs = np.array(pcs)

    pc_analog = -vpre / (LSB_I * r_ti) + (theta + 1)
    A2 = np.vstack([pcs, np.ones_like(pcs)]).T
    slope, ic = np.linalg.lstsq(A2, pc_analog, rcond=None)[0]
    # decisions: ideal comparator on the analog differential vs true sign
    truth = np.sign(pcs - (theta + 1))
    keep = truth != 0
    raw = np.sign(-vpre)                      # vpre<0 <=> pc>theta+1
    agree_raw = float(np.mean(raw[keep] == truth[keep]))
    # one-point recalibration: undo fitted slope/intercept, then decide
    pc_rec = (pc_analog - ic) / slope
    rec = np.sign(pc_rec - (theta + 1))
    agree_rec = float(np.mean(rec[keep] == truth[keep]))
    return {"N": N, "slope": round(float(slope), 4),
            "far_end_ir_mV": round(float(np.mean(vfar)) * 1e3, 3),
            "agree_raw_pct": round(agree_raw * 100, 1),
            "agree_recal_pct": round(agree_rec * 100, 1),
            "n_decisions": int(keep.sum())}


def main() -> None:
    rows = [scan(N) for N in NS]
    for r in rows:
        print(f"N={r['N']:3d}: slope {r['slope']:.4f}  far-end IR "
              f"{r['far_end_ir_mV']:6.2f} mV  agree raw {r['agree_raw_pct']:5.1f}%"
              f"  recal {r['agree_recal_pct']:5.1f}%  (n={r['n_decisions']})")
    out_csv = HERE / "nodal_ir_scaling.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    (HERE / "nodal_ir_scaling_summary.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8")
    print(f"wrote {out_csv.name} + summary json")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
    Ns = [r["N"] for r in rows]
    ax[0].semilogx(Ns, [r["slope"] for r in rows], "o-", color="#5E3F8C",
                   lw=2, base=2)
    ax[0].axhline(0.9, color="grey", ls=":", lw=1.2)
    ax[0].set_xlabel("column height N"); ax[0].set_ylabel("analog slope")
    ax[0].set_title("Ladder compression vs column height")
    ax[0].grid(alpha=0.3, which="both")
    ax[1].semilogx(Ns, [r["agree_raw_pct"] for r in rows], "o-",
                   color="#A82038", lw=2, base=2, label="raw")
    ax[1].semilogx(Ns, [r["agree_recal_pct"] for r in rows], "s--",
                   color="#1A6B5A", lw=2, base=2,
                   label="after 1-point recalibration")
    ax[1].set_xlabel("column height N")
    ax[1].set_ylabel("decision agreement (%)")
    ax[1].set_title("Threshold absorption: raw vs recalibrated")
    ax[1].legend(fontsize=9); ax[1].grid(alpha=0.3, which="both")
    fig.tight_layout()
    out = REPO / "figures" / "nodal_ir_scaling.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
