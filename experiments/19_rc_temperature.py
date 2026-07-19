"""19 -- Temperature as a relaxation-time knob (device operation guidance).

The thermal-stability factor is Delta = E_b / (k_B T), so at fixed barrier
height it scales as Delta(T) = Delta_300 * 300 / T. Because the relaxation time
is exponential in Delta, the reservoir's fading memory tau(T) = tau_0 exp(Delta(T))/2
is strongly temperature dependent -- a challenge for deployment. This experiment
shows the sensitivity and a simple operation recipe that neutralises it.

  (a) tau(T) at zero bias -- exponential temperature sensitivity
  (b) memory capacity vs T at a FIXED reservoir clock dt -- a narrow window
  (c) the thermal clock recipe: optimal dt(T) = tau(T)/2.31 (the matching law)
  (d) memory capacity vs T WITH clock compensation -- a wide, flat window

All mean-field, to isolate the device timescale from shot noise. The barrier
E_b is set so Delta(300 K) = 4.91 (the Chapter 2.3 device).

Run from the repo root:

    python experiments/19_rc_temperature.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.device.telegraph import TelegraphParams, relaxation_time  # noqa: E402
from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402

PURPLE, RED, DEEP, GREEN = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A"
DELTA_300 = 4.91
MATCH_RATIO = 2.31           # tau* / dt from experiment 15
DT_FIXED = 8e-9


# As-built calibrated chain (T2-2, LLG dual-anchored to <1%): Bloch M_s +
# Callen-Callen K_i through the 81%-compensated K_eff -- replaces the
# kT-only simplification Delta_300*300/T that overestimated the high-T
# relaxation time by ~2x (see the chapter's tau-axis correction footnote).
from smtj_pbnn_sim.device.thermal_scaling import delta_of_T  # noqa: E402


def main() -> None:
    t0 = time.time()
    u = tasks.memory_capacity_inputs(1500, seed=2)
    temps = np.array([250, 270, 290, 300, 320, 350, 380, 410])

    def mc(T, dt):
        cfg = ReservoirConfig(n_nodes=120, mode="meanfield",
                              params=TelegraphParams(Delta=delta_of_T(T)),
                              effective_spectral_radius=0.6,
                              effective_input_scale=0.5, dt=dt, delta_cv=0.25,
                              seed=1)
        X = SMTJReservoir(cfg, 1).run(u, washout=100)
        return memory_capacity(X, u[100:], max_delay=30)[0]

    tau_T = np.array([relaxation_time(0.0, Delta=delta_of_T(T)) for T in temps])
    dt_opt = tau_T / MATCH_RATIO
    mc_fixed = np.array([mc(T, DT_FIXED) for T in temps])
    mc_comp = np.array([mc(T, float(dt)) for T, dt in zip(temps, dt_opt)])

    print("tau(0) at 250/300/410 K: "
          f"{tau_T[0]*1e9:.0f} / {relaxation_time(0.0, Delta=DELTA_300)*1e9:.0f} / "
          f"{tau_T[-1]*1e9:.0f} ns")
    print(f"MC spread, fixed clock : {mc_fixed.min():.2f}-{mc_fixed.max():.2f} "
          f"(range {mc_fixed.max()-mc_fixed.min():.2f})")
    print(f"MC spread, compensated : {mc_comp.min():.2f}-{mc_comp.max():.2f} "
          f"(range {mc_comp.max()-mc_comp.min():.2f})")

    # ----------------------------- figure ---------------------------------#
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    ax[0, 0].semilogy(temps, tau_T * 1e9, "o-", color=RED, lw=2)
    ax[0, 0].axvline(300, color="grey", ls=":", lw=1.2)
    ax[0, 0].set_xlabel("temperature T (K)")
    ax[0, 0].set_ylabel(r"$\tau(T)$ at zero bias (ns)")
    ax[0, 0].set_title(r"$\tau \propto \exp(E_b/k_BT)$ -- strong T sensitivity")
    ax[0, 0].grid(alpha=0.3, which="both")

    ax[0, 1].plot(temps, mc_fixed, "o-", color=PURPLE, lw=2)
    ax[0, 1].axvline(300, color="grey", ls=":", lw=1.2)
    ax[0, 1].set_xlabel("temperature T (K)")
    ax[0, 1].set_ylabel("memory capacity")
    ax[0, 1].set_title(f"Fixed clock (dt={DT_FIXED*1e9:.0f} ns): MC drifts with T")
    ax[0, 1].grid(alpha=0.3)

    ax[1, 0].semilogy(temps, dt_opt * 1e9, "s-", color=DEEP, lw=2)
    ax[1, 0].set_xlabel("temperature T (K)")
    ax[1, 0].set_ylabel(r"optimal clock $dt = \tau(T)/2.31$ (ns)")
    ax[1, 0].set_title("Thermal clock recipe (from the matching law)")
    ax[1, 0].grid(alpha=0.3, which="both")

    ax[1, 1].plot(temps, mc_fixed, "o--", color=PURPLE, lw=1.6, alpha=0.7,
                  label="fixed clock")
    ax[1, 1].plot(temps, mc_comp, "s-", color=GREEN, lw=2, label="clock-compensated")
    ax[1, 1].set_xlabel("temperature T (K)")
    ax[1, 1].set_ylabel("memory capacity")
    ax[1, 1].set_title("Clock compensation flattens the window")
    ax[1, 1].legend(fontsize=10)
    ax[1, 1].grid(alpha=0.3)

    fig.suptitle("sMTJ reservoir: temperature dependence and clock compensation",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "19_rc_temperature.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
