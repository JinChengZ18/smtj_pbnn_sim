"""15 -- Device-optimization guidance for sMTJ reservoir computing.

Answers a fab-actionable question: *what sMTJ should you build for reservoir
computing, and how does it differ from the PBNN write device?* Everything is
run in the noise-free mean-field mode so the conclusions are about device
physics, not shot noise.

The memory of a (non-recurrent) sMTJ reservoir node IS its relaxation time
tau(V) = tau_0 exp(Delta)/2, so the thermal-stability factor Delta is the
primary device knob. Four panels:

  (a) memory-capacity map over (Delta, task step dt) -- a diagonal ridge
  (b) optimal Delta* and tau* vs dt -- the timescale-matching law tau* ~ 2 dt
  (c) MC vs Delta at a fixed timescale -- RC optimum sits BELOW the PBNN device
  (d) memory/nonlinearity tradeoff swept by input drive -- the Pareto front

Reference points: the Chapter 2.3 PBNN write device has Delta = 4.91.

Run from the repo root:

    python experiments/15_rc_device_optimization.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.device.telegraph import (                       # noqa: E402
    TelegraphParams, relaxation_time)
from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout, nrmse, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402

PURPLE, RED, DEEP, GREEN, LILAC = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4"
PBNN_DELTA = 4.91                       # Chapter 2.3 write device
N_NODES = 120


def _reservoir(Delta, dt, sr, input_scale, V_bias=0.0):
    return SMTJReservoir(
        ReservoirConfig(n_nodes=N_NODES, mode="meanfield",
                        params=TelegraphParams(Delta=Delta),
                        effective_spectral_radius=sr,
                        effective_input_scale=input_scale,
                        dt=dt, V_bias=V_bias, delta_cv=0.25, seed=1),
        n_inputs=1)


def main() -> None:
    t0 = time.time()

    # Memory uses the device timescale alone -> no recurrence (sr=0).
    u_mc = tasks.memory_capacity_inputs(1500, seed=2)

    def mc_of(Delta, dt):
        X = _reservoir(Delta, dt, 0.0, 0.5).run(u_mc, washout=100)
        return memory_capacity(X, u_mc[100:], max_delay=40)[0]

    # (a) MC map over (Delta, dt) ------------------------------------------#
    Deltas = np.linspace(1.5, 6.5, 14)
    dts = np.array([4, 8, 16, 32, 64, 120]) * 1e-9
    grid = np.array([[mc_of(D, dt) for D in Deltas] for dt in dts])

    # (b) optimal Delta* and tau* vs dt ------------------------------------#
    dt_fine = np.array([4, 6, 10, 16, 25, 40, 64, 100, 160]) * 1e-9
    Delta_dense = np.linspace(1.5, 6.5, 26)
    best_Delta, best_tau = [], []
    for dt in dt_fine:
        mcs = [mc_of(D, dt) for D in Delta_dense]
        D_star = Delta_dense[int(np.argmax(mcs))]
        best_Delta.append(D_star)
        best_tau.append(float(relaxation_time(0.0, Delta=D_star)))
    best_Delta = np.array(best_Delta)
    best_tau = np.array(best_tau)

    # (c) MC vs Delta at fixed dt = 8 ns -----------------------------------#
    dt_fix = 8e-9
    mc_curve = np.array([mc_of(D, dt_fix) for D in Delta_dense])
    D_rc = Delta_dense[int(np.argmax(mc_curve))]

    # (d) memory / nonlinearity tradeoff vs operating-point bias -----------#
    # tanh is an ODD nonlinearity, so at V_bias = 0 the node cannot form the
    # even product u[t-1]*u[t-2]. A nonzero operating-point bias breaks that
    # symmetry -- buying nonlinearity at the cost of memory (tau peaks at V=0).
    u_pm, y_pm = tasks.product_memory(1600, seed=5)
    v_biases = np.array([0.0, 0.02, 0.04, 0.06, 0.09, 0.12, 0.16, 0.20])
    lin_mc, nonlin_score = [], []
    for vb in v_biases:
        res = _reservoir(3.5, dt_fix, 0.6, 1.5, V_bias=float(vb))
        Xm = res.run(u_mc, washout=100)
        lin_mc.append(memory_capacity(Xm, u_mc[100:], max_delay=30)[0])
        Xp = res.run(u_pm, washout=100)
        y_al = y_pm[100:]
        ntr = 1000
        ro = RidgeReadout(alpha=1e-4).fit(Xp[:ntr], y_al[:ntr])
        nonlin_score.append(max(0.0, 1.0 - nrmse(y_al[ntr:], ro.predict(Xp[ntr:]))))
    lin_mc = np.array(lin_mc)
    nonlin_score = np.array(nonlin_score)

    print(f"RC-optimal Delta at dt=8ns : {D_rc:.2f}  "
          f"(tau={relaxation_time(0.0, Delta=D_rc)*1e9:.1f} ns)  "
          f"vs PBNN write device Delta={PBNN_DELTA}")
    print(f"timescale-matching ratio tau*/dt : "
          f"{np.mean(best_tau / dt_fine):.2f} +/- {np.std(best_tau/dt_fine):.2f}")

    # ----------------------------- figure ---------------------------------#
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    # (a) heatmap
    im = ax[0, 0].imshow(grid, aspect="auto", origin="lower", cmap="viridis",
                         extent=[Deltas[0], Deltas[-1],
                                 dts[0] * 1e9, dts[-1] * 1e9])
    ax[0, 0].set_yscale("log")
    ax[0, 0].axvline(PBNN_DELTA, color="white", ls="--", lw=1.6)
    ax[0, 0].text(PBNN_DELTA + 0.05, dts[-1] * 1e9 * 0.6, "PBNN\nwrite",
                  color="white", fontsize=9)
    ax[0, 0].set_xlabel(r"thermal stability $\Delta$")
    ax[0, 0].set_ylabel("task step dt (ns)")
    ax[0, 0].set_title("Memory capacity map  MC($\\Delta$, dt)")
    fig.colorbar(im, ax=ax[0, 0], label="memory capacity")

    # (b) matching law
    axb = ax[0, 1]
    axb.plot(dt_fine * 1e9, best_tau * 1e9, "o-", color=PURPLE, lw=2,
             label=r"optimal $\tau^*$")
    axb.plot(dt_fine * 1e9, 2.0 * dt_fine * 1e9, "k:", lw=1.5,
             label=r"$\tau^* = 2\,dt$")
    axb.set_xlabel("task step dt (ns)")
    axb.set_ylabel(r"optimal relaxation time $\tau^*$ (ns)")
    axb.set_title("Timescale-matching law")
    axb.legend(fontsize=10)
    axb.grid(alpha=0.3)
    axb2 = axb.twinx()
    axb2.plot(dt_fine * 1e9, best_Delta, "s--", color=RED, lw=1.4, alpha=0.8)
    axb2.axhline(PBNN_DELTA, color=RED, ls=":", lw=1.2)
    axb2.set_ylabel(r"optimal $\Delta^*$ (red)", color=RED)
    axb2.tick_params(axis="y", labelcolor=RED)

    # (c) MC vs Delta at fixed dt
    ax[1, 0].plot(Delta_dense, mc_curve, "-", color=DEEP, lw=2.2)
    ax[1, 0].axvline(D_rc, color=GREEN, lw=2,
                     label=f"RC optimum $\\Delta$={D_rc:.1f}")
    ax[1, 0].axvline(PBNN_DELTA, color=RED, ls="--", lw=2,
                     label=f"PBNN device $\\Delta$={PBNN_DELTA}")
    ax[1, 0].set_xlabel(r"thermal stability $\Delta$")
    ax[1, 0].set_ylabel("memory capacity")
    ax[1, 0].set_title("RC wants a lower barrier than PBNN (dt = 8 ns)")
    ax[1, 0].legend(fontsize=10)
    ax[1, 0].grid(alpha=0.3)

    # (d) memory/nonlinearity tradeoff
    ax[1, 1].plot(lin_mc, nonlin_score, "-", color="grey", lw=1, alpha=0.6)
    sc = ax[1, 1].scatter(lin_mc, nonlin_score, c=v_biases * 1e3, cmap="plasma",
                          s=80, edgecolor="black", zorder=3)
    ax[1, 1].set_xlabel("linear memory capacity")
    ax[1, 1].set_ylabel(r"nonlinear score  $1-$NRMSE  ($u_{t-1}u_{t-2}$)")
    ax[1, 1].set_title("Memory / nonlinearity tradeoff (bias)")
    fig.colorbar(sc, ax=ax[1, 1], label=r"operating-point bias $V_{bias}$ (mV)")
    ax[1, 1].grid(alpha=0.3)

    fig.suptitle("Device-optimization guidance for sMTJ reservoir computing",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "15_rc_device_optimization.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
