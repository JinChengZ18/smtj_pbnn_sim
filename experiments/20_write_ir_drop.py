#!/usr/bin/env python3
"""Experiment 20 -- write-line IR drop and IR-aware pre-distortion (sky130-grounded).

Exercises ``smtj_pbnn_sim.array.ir_drop`` (the resistive-ladder solver grounded in the sky130
extresist extraction): along a tall write column the delivered voltage droops with row distance,
collapsing the remote switching probability; the per-row pre-distortion restores the target at every
row. Reproduces the high-column write-fidelity limit from the device-circuit co-design.

Run:  PYTHONPATH=src python experiments/20_write_ir_drop.py
Outputs: figures/20_write_ir_drop.png  +  a printed summary (per-N worst-case IR fraction).
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from smtj_pbnn_sim.array import ir_drop as ir

FIGS = Path(__file__).resolve().parent.parent / "figures"
BLACK, RED, BLUE = "#1a1a1a", "#c0392b", "#2c5aa0"


def v_for_psw(p: float) -> float:
    return ir.V_TH + ir.V_T * math.log(p / (1.0 - p))


def main():
    p_target = 0.90
    v_target = v_for_psw(p_target)

    # worst-case IR fraction vs column height (grounded met2 round-trip)
    print(f"target p_sw = {p_target}  ->  V_target = {v_target*1e3:.1f} mV  "
          f"(I_wr = {ir._i_wr(v_target)*1e3:.3f} mA, R_wire = {ir.R_WIRE_PER_CELL_MET2} ohm/cell)")
    for N in (64, 256, 1024):
        frac = ir.estimate_ir_drop(N)
        v_far = ir.delivered_voltage(v_target, N)[-1]
        print(f"  N={N:5d}:  worst-case IR fraction {100*frac:4.1f}%   "
              f"remote V {v_far*1e3:6.1f} mV   remote p_sw {ir.psw(v_far):.3f}")

    N = 256
    rows = list(range(N))
    v_un = ir.delivered_voltage(v_target, N, predistort=False)
    v_pd = ir.delivered_voltage(v_target, N, predistort=True)
    p_un = ir.psw_profile(v_target, N, predistort=False)
    p_pd = ir.psw_profile(v_target, N, predistort=True)

    fig, ax = plt.subplots(1, 2, figsize=(10.4, 3.8))
    ax[0].plot(rows, [v*1e3 for v in v_un], color=RED, lw=1.9, label="uncompensated")
    ax[0].plot(rows, [v*1e3 for v in v_pd], color=BLUE, lw=1.9, ls="--", label="IR pre-distorted")
    ax[0].axhline(v_target*1e3, color="#999", lw=0.9, ls=":")
    ax[0].set_xlabel("row (distance from driver)"); ax[0].set_ylabel("delivered write voltage (mV)")
    ax[0].set_title("(a) write-line voltage along the column (N=256)", fontsize=10.5)
    ax[0].legend(fontsize=8.5)

    ax[1].plot(rows, p_un, color=RED, lw=1.9, label="uncompensated")
    ax[1].plot(rows, p_pd, color=BLUE, lw=1.9, ls="--", label="IR pre-distorted")
    ax[1].axhline(p_target, color="#999", lw=0.9, ls=":")
    ax[1].set_xlabel("row (distance from driver)"); ax[1].set_ylabel("switching probability P$_{sw}$")
    ax[1].set_ylim(-0.03, 1.03)
    ax[1].set_title("(b) remote write-probability collapse + fix", fontsize=10.5)
    ax[1].legend(fontsize=8.5)
    for a in ax:
        a.grid(True, color="#e8e8e8", lw=0.7); a.set_axisbelow(True)
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / "20_write_ir_drop.png", dpi=200, bbox_inches="tight")
    print(f"\nremote (row {N-1}) p_sw: {p_un[-1]:.3f} uncompensated -> {p_pd[-1]:.3f} pre-distorted")
    print(f"Figure saved: {FIGS / '20_write_ir_drop.png'}")


if __name__ == "__main__":
    main()
