"""03 -- Cross-pulse-width Néel-Brown fit and joint Psw(V, t_w) heatmap.

Demonstrates the layer-1 (cross-pulse-width) view of the joint write
probability model. Reads V_th(t_w) data points (which are normally
extracted from hysteresis sweeps in Chapter 2.3 -- here we reproduce the
chapter-2 Device A linear regression), fits (Delta, V_c0), and plots the
2-D Psw(V, t_w) heatmap with the 50 % contour.

Run from the repo root:

    python experiments/03_nb_cross_pulse_width.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.device.calibration import fit_neel_brown_from_vth_vs_tw   # noqa: E402
from smtj_pbnn_sim.device.arrhenius   import psw_neel_brown                  # noqa: E402


# Chapter 2.3 Section 2.3.3 cross-pulse-width regression for Device A:
#   V_AP->P  (t_w)  = 0.82 - 0.17 ln(t_w / ns)  V
#   V_P->AP  (t_w)  = -0.79 + 0.18 ln(t_w / ns) V  (sign flipped: |V_th|)
# Reconstruct the four fit points (0.75, 1, 2, 5 ns) from the two regressions.
def synth_vth_table() -> pd.DataFrame:
    rows = []
    for t_ns in (0.75, 1.0, 2.0, 5.0):
        V_AP_to_P = 0.82 - 0.17 * np.log(t_ns)         # AP -> P, positive
        V_P_to_AP = 0.79 - 0.18 * np.log(t_ns)         # |V| of P -> AP
        rows.append(("A", "AP->P", t_ns * 1e-9, float(V_AP_to_P)))
        rows.append(("A", "P->AP", t_ns * 1e-9, float(V_P_to_AP)))
    return pd.DataFrame(rows, columns=["device_id", "direction", "t_p", "V_th"])


def main() -> None:
    df = synth_vth_table()
    print("V_th(t_w) reconstructed from Chapter 2.3 Section 2.3.3 regressions:")
    print(df.to_string(index=False))
    print()

    for direction in ("AP->P", "P->AP"):
        sub = df[df.direction == direction]
        nb = fit_neel_brown_from_vth_vs_tw(sub, tau_0=1e-9)
        print(f"  Device A, {direction}:")
        print(f"    Delta = {nb.Delta:.2f}  (Chapter 2.3 reports "
              f"{5.15 if direction == 'AP->P' else 4.91})")
        print(f"    V_c0  = {nb.V_c0*1e3:.0f} mV (Chapter 2.3 reports "
              f"{884 if direction == 'AP->P' else 857} mV)")
        print(f"    R^2   = {nb.r2:.4f}")
        print()

    # Joint heatmap of Psw(V, t_w) for AP->P
    sub_ap = df[df.direction == "AP->P"]
    nb_ap = fit_neel_brown_from_vth_vs_tw(sub_ap, tau_0=1e-9)

    Vs = np.linspace(0.4, 1.1, 200)
    tps = np.logspace(np.log10(0.5e-9), np.log10(20e-9), 80)
    P = np.zeros((len(tps), len(Vs)))
    for i, tp in enumerate(tps):
        P[i] = psw_neel_brown(Vs, t_p=float(tp),
                              tau_0=nb_ap.tau_0_assumed,
                              Delta=nb_ap.Delta, V_c0=nb_ap.V_c0)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    im = ax.pcolormesh(Vs * 1e3, tps * 1e9, P, cmap="Purples",
                       shading="auto", vmin=0, vmax=1)
    cs = ax.contour(Vs * 1e3, tps * 1e9, P, levels=[0.5],
                    colors="black", linestyles="--")
    ax.clabel(cs, fmt={0.5: "P$_{sw}$ = 0.5"}, fontsize=10)

    # Overlay the four V_th data points used for the fit
    ax.scatter(sub_ap["V_th"] * 1e3, sub_ap["t_p"] * 1e9,
               s=80, edgecolor="black", facecolor="white",
               linewidth=1.5, zorder=10, label="V$_{th}$ (hysteresis)")

    ax.set_yscale("log")
    ax.set_xlabel("V$_{SOT}$ (mV)")
    ax.set_ylabel("t$_w$ (ns)")
    ax.set_title("Joint write probability P$_{sw}$(V, t$_w$) -- "
                 "Device A, AP->P, Néel-Brown")
    ax.legend(loc="upper right")
    fig.colorbar(im, ax=ax, label="P$_{sw}$")
    fig.tight_layout()
    out = REPO / "figures" / "03_nb_cross_pulse_width.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"Figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
