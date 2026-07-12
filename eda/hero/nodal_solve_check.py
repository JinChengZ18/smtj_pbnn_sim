#!/usr/bin/env python3
"""Exact nodal-solve cross-check of the replay column netlist (T3-5).

Solves the SAME linear network the ngspice deck builds -- bit-line
ladders (R_seg segments, 1 mohm taps), finite-gain (2e4) virtual-ground
TIA with feedback R_TI, common-mode cancellation and threshold current
sources -- for every trial state regenerated bit-exactly from the
harness seed, and compares the pre-clock differential (vpre) against
the committed ngspice arrays. This is the archived, faithful version of
the bring-up cross-check; an earlier UNARCHIVED simplified solver
(ideal virtual ground, no ladder taps) gave slope 0.71 and was quoted
in commit 9e36c28 -- the exact solve reproduces ngspice to sub-uV and
the committed slope fit to four decimals.

Run (Windows or WSL): python eda/hero/nodal_solve_check.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent

# constants mirrored from replay_column_cosim.py
N = 64
RP, TMR, VR = 4900.0, 1.0, 0.1
GP, GAP = 1.0 / RP, 1.0 / (RP * (1.0 + TMR))
LSB_I = (VR / 2.0) * (GP - GAP)
R_TI = 0.6 / (2.0 * 3.0 * np.sqrt(N) * LSB_I)
R_SEG = 0.125 / 0.23 * 2.0
R_TAP = 1e-3
VCM = 0.9
GAIN = 2e4
SEED = 20260713
TRIALS_PER_DECK = 100
N_DECKS = 6
I_CM = N * (GP + GAP) / 2.0 * (VR / 2.0)


def solve_line(gcell: np.ndarray, i_inject: float) -> tuple:
    """One bit-line: taps t0..t63 (cell side), ladder b0..b63, TIA.

    Unknowns: tap nodes (folded into ladder nodes via R_TAP ~ 0), ladder
    nodes v[0..N-1] (v[N-1] = TIA virtual-ground node vg), and the TIA
    output node vo with vo = VCM + GAIN (VCM - vg), feedback R_TI from
    vo to vg. i_inject = dc sources at the vg node (cancellation +
    threshold), positive = extracted from the node.
    Returns (vo, vg, v0) -- output, virtual ground, far-end ladder node.
    """
    Vdrv = VCM + VR / 2.0
    g_cell_eff = 1.0 / (1.0 / gcell + R_TAP)      # cell R + tap in series
    gseg = 1.0 / R_SEG
    gti = 1.0 / R_TI
    # nodes 0..N-1 ladder; node N = TIA output
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
    # feedback R_TI between vg (node N-1) and vo (node N)
    A[N - 1, N - 1] += gti
    A[N - 1, N] -= gti
    A[N, N] += gti
    A[N, N - 1] -= gti
    # dc sources at vg (positive = extracted)
    b[N - 1] -= i_inject
    # op-amp row: vo + GAIN*vg = VCM*(1+GAIN)  (vo = VCM + GAIN(VCM-vg))
    A[N, :] = 0.0
    A[N, N] = 1.0
    A[N, N - 1] = GAIN
    b[N] = VCM * (1.0 + GAIN)
    # ideal E-source supplies feedback current; restore KCL at vg only
    v = np.linalg.solve(A, b)
    return float(v[N]), float(v[N - 1]), float(v[0])


def main() -> None:
    rng = np.random.default_rng(SEED)
    p = np.clip(rng.uniform(0.1, 0.9, N), 0.0, 1.0)
    mu_pc = float(np.sum(2 * p - 1))
    theta = 2 * int(round(mu_pc / 2.0))
    i_th = (theta + 1) * LSB_I / 2.0

    report = {}
    for tag in ("os0", "os9"):
        npz = HERE / f"_replay_trials_{tag}.npz"
        ref = np.load(npz) if npz.exists() else None
        vpre, pcs, vfar = [], [], []
        for _ in range(N_DECKS):
            states = np.where(
                rng.random((TRIALS_PER_DECK, N)) < p[None, :], 1, -1)
            for srow in states:
                gp_line = np.where(srow > 0, GP, GAP)
                gn_line = np.where(srow > 0, GAP, GP)
                vop, vgp, v0p = solve_line(gp_line, I_CM + i_th)
                von, vgn, _ = solve_line(gn_line, I_CM - i_th)
                vpre.append(vop - von)
                vfar.append(v0p - vgp)
                pcs.append(int(srow.sum()))
        vpre = np.array(vpre)
        pcs = np.array(pcs)
        pc_analog = -vpre / (LSB_I * R_TI) + (theta + 1)
        A2 = np.vstack([pcs, np.ones_like(pcs)]).T
        slope, ic = np.linalg.lstsq(A2, pc_analog, rcond=None)[0]
        line = (f"{tag}: slope {slope:.4f} intercept {ic:+.3f} pc, "
                f"far-end IR {np.mean(vfar) * 1e3:.2f} mV")
        if ref is not None and "vpre" in ref:
            dmax = float(np.max(np.abs(-vpre - ref["vpre"])))
            line += f", max |vpre - ngspice| = {dmax:.2e} V"
        print(line, flush=True)
        report[tag] = dict(slope=float(slope), intercept=float(ic))


if __name__ == "__main__":
    main()
