"""02 -- Wafer-average Monte Carlo at the PDK-baseline CV(Delta) = 7.7%.

Reproduces the chapter-2.3 cross-check that the joint model

    beta^eff(CV) = eta_c * F(CV) * beta_NB^analytic

predicts the measured beta_s = 44.6 V^-1 at CV(Delta) = 7.7 %.

The script sweeps CV(Delta) from 0 % up to 60 %, draws N = 20000 Delta_i
samples per CV, refits a Sigmoid to the wafer-average Psw curve, and plots
beta^eff vs CV. The PDK baseline marker is drawn at CV = 7.7 %.

Run from the repo root:

    python experiments/02_wafer_average_mc.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import math

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.device.arrhenius import psw_neel_brown   # noqa: E402
from smtj_pbnn_sim.device.calibration import fit_sigmoid_params  # noqa: E402
import pandas as pd                                                # noqa: E402


# ---- Chapter 2.3 primary reference ------------------------------------------#
DELTA_NOM = 4.91
V_C0_NOM  = 0.857
TAU_0     = 1.0e-9
T_P       = 0.75e-9
ETA_C     = 5.34
N_DEV     = 20_000
SEED      = 42

# beta_NB analytic at V_th
BETA_NB = 2.0 * math.log(2.0) * (DELTA_NOM / V_C0_NOM)
print(f"beta_NB analytic (Delta={DELTA_NOM}, V_c0={V_C0_NOM} V) = {BETA_NB:.2f} V^-1\n")


def wafer_average(cv_delta: float) -> tuple[float, float, float]:
    """Return (beta_eff_fit, V_th_fit, R^2) of the wafer-average Sigmoid."""
    rng = np.random.default_rng(SEED)
    Delta_i = np.maximum(
        DELTA_NOM * (1.0 + cv_delta * rng.standard_normal(N_DEV)),
        0.5,
    )
    V = np.linspace(0.78, 1.10, 81)
    P_avg = np.zeros_like(V)
    for D in Delta_i:
        # NB law per device, then average.
        P_avg += psw_neel_brown(V, t_p=T_P, tau_0=TAU_0, Delta=D, V_c0=V_C0_NOM)
    P_avg /= N_DEV
    df = pd.DataFrame({"V": V, "P_sw": P_avg, "t_p": T_P})
    sp = fit_sigmoid_params(df)
    return sp.beta_s, sp.V_th, sp.r2


def main() -> None:
    cvs = np.array([0.00, 0.03, 0.05, 0.077, 0.10, 0.15, 0.20, 0.30, 0.40, 0.60])
    rows = []
    for cv in cvs:
        beta_eff, V_th, r2 = wafer_average(float(cv))
        F = beta_eff / BETA_NB
        beta_pred = ETA_C * F * BETA_NB
        rows.append((cv, beta_eff, V_th, r2, F, beta_pred))
        print(f"  CV(Delta) = {cv*100:5.1f}%  ->  "
              f"beta_NB_fit = {beta_eff:5.2f} V^-1, F = {F:.3f}, "
              f"beta^eff = eta_c*F*beta_NB = {beta_pred:5.2f} V^-1, "
              f"V_th = {V_th*1e3:6.1f} mV, R^2 = {r2:.4f}")

    print()
    cv_pdk = 0.077
    beta_eff_pdk, _, _ = wafer_average(cv_pdk)
    F_pdk = beta_eff_pdk / BETA_NB
    pred_pdk = ETA_C * F_pdk * BETA_NB
    print(f"PDK baseline CV(Delta) = 7.7 %:")
    print(f"  F(7.7 %)              = {F_pdk:.3f}    (Chapter 2.3 reports 0.997)")
    print(f"  joint prediction      = {pred_pdk:.2f} V^-1")
    print(f"  measured beta_s       = 44.6 V^-1   (Chapter 2.3, Device A P->AP)")
    print(f"  prediction / measured = {pred_pdk / 44.6 * 100:.1f}%")

    # Plot
    arr = np.array(rows)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.plot(arr[:, 0] * 100, arr[:, 5], "o-", color="#A82038", lw=2,
            label=r"$\beta^{eff} = \eta_c \cdot \mathcal{F}(CV)\cdot \beta_{NB}^{fit}$")
    ax.axhline(BETA_NB, color="#1F5FA8", lw=1.2, ls="--",
               label=fr"$\beta_{{NB}}$ analytic = {BETA_NB:.2f} V$^{{-1}}$")
    ax.axhline(44.6, color="#1A6B5A", lw=1.2, ls=":",
               label=r"measured $\beta_s = 44.6$ V$^{-1}$ (Device A, P$\to$AP)")
    ax.scatter([7.7], [pred_pdk], s=180, marker="*", color="#C47A00",
               edgecolor="black", zorder=10, label=f"PDK baseline 7.7%")
    ax.set_xlabel("CV(Delta) (%)")
    ax.set_ylabel(r"$\beta$ (V$^{-1}$)")
    ax.set_yscale("log")
    ax.set_title("Wafer-average Sigmoid slope vs. CV($\\Delta$) "
                 "(N = 20000, t$_w$ = 0.75 ns)")
    ax.grid(alpha=0.3, which="both")
    ax.legend(loc="upper right")
    fig.tight_layout()
    out = REPO / "figures" / "02_wafer_average_mc.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
