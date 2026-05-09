"""01 -- Device calibration from the measured Chapter 2.3 CSV.

Reads ``data/smtj_psw_curves/measured_0p75ns.csv``, fits per-(device,
direction) Sigmoid parameters, writes the primary-reference YAML to
``configs/device/sot_smtj_devA_pAP_0p75ns.yaml``, and plots the four
fitted curves overlaid with the measured points.

Run from the repo root:

    python experiments/01_device_calibration.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.device.calibration import (   # noqa: E402
    fit_per_device_direction, fit_sigmoid_params, write_device_yaml,
)


CSV   = REPO / "data" / "smtj_psw_curves" / "measured_0p75ns.csv"
YAML  = REPO / "configs" / "device" / "sot_smtj_devA_pAP_0p75ns.yaml"
FIGS  = REPO / "figures"


def main() -> None:
    df = pd.read_csv(CSV)
    print(f"Loaded {len(df)} measured points from {CSV.relative_to(REPO)}\n")

    # Per-group summary
    summary = fit_per_device_direction(df)
    cols = ["device_id", "direction", "V_th", "V_T", "beta_s", "r2", "n_points"]
    print("Per-(device, direction) Sigmoid fits:")
    print(summary[cols].to_string(index=False))
    print()

    # Primary reference: Device A, P->AP
    primary = df[(df.device_id == "A") & (df.direction == "P->AP")]
    sp = fit_sigmoid_params(primary)
    print(f"Primary reference (Device A, P->AP, t_w = 0.75 ns):")
    print(f"  V_th   = {sp.V_th*1e3:.1f} mV   (Chapter 2.3 reports 894 mV)")
    print(f"  beta_s = {sp.beta_s:.1f} V^-1  (Chapter 2.3 reports 44.6 V^-1)")
    print(f"  R^2    = {sp.r2:.3f}        (Chapter 2.3 reports 0.993)")
    print()

    write_device_yaml(
        sigmoid=sp,
        out_path=str(YAML),
        eta_c=5.34,
        R_P=4.9e3, TMR=1.0, R_SOT=776.0,
        note="Auto-fit by 01_device_calibration.py from Chapter 2.3 CSV.",
    )
    print(f"Device YAML written to {YAML.relative_to(REPO)}")

    # Overlay plot of all four fits
    FIGS.mkdir(exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    layout = [("A", "AP->P"), ("A", "P->AP"), ("B", "AP->P"), ("B", "P->AP")]
    V_dense = np.linspace(0.78, 1.12, 300)
    for ax, key in zip(axes.flat, layout):
        dev, dirn = key
        sub = df[(df.device_id == dev) & (df.direction == dirn)]
        sp_i = fit_sigmoid_params(sub)
        P_fit = 1.0 / (1.0 + np.exp(-(V_dense - sp_i.V_th) / sp_i.V_T))
        ax.scatter(sub["V"] * 1e3, sub["P_sw"], s=40, edgecolor="#5E3F8C",
                   facecolor="white", linewidth=1.5, zorder=4,
                   label="measured (100 reps)")
        ax.plot(V_dense * 1e3, P_fit, lw=2.0, color="#5E3F8C",
                label=(f"fit: V$_{{th}}$ = {sp_i.V_th*1e3:.1f} mV, "
                       f"$\\beta_s$ = {sp_i.beta_s:.1f} V$^{{-1}}$"))
        ax.axhline(0.5, color="gray", lw=0.5, ls=":")
        ax.set_xlim(780, 1120)
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel("V$_{SOT}$ (mV)")
        ax.set_ylabel("P$_{sw}$")
        ax.set_title(f"Device {dev}, {dirn}")
        ax.legend(loc="lower right", fontsize=10)
        ax.grid(alpha=0.3)
    fig.suptitle("Sigmoid calibration of measured Psw at t$_w$ = 0.75 ns "
                 "(Chapter 2.3 data)", fontsize=14)
    fig.tight_layout()
    out_png = FIGS / "01_device_calibration.png"
    fig.savefig(out_png, dpi=180, bbox_inches="tight")
    print(f"QA figure  written to {out_png.relative_to(REPO)}")


if __name__ == "__main__":
    main()
