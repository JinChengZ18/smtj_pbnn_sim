"""14 -- sMTJ reservoir-computing prototype.

Demonstrates that the *same* Chapter 2.3 sMTJ device, run as a stateful
two-state telegraph node instead of a memoryless PBNN p-bit, is a viable
reservoir-computing substrate. Six panels:

  (a) device transfer  <s>_inf(V) = tanh(Delta V / V_c0)  -- the nonlinearity
  (b) correlation time tau(V) = 1/(r_up+r_dn)             -- the tunable memory
  (c) forgetting curve  MC_k vs delay k   (ideal vs real device)
  (d) memory capacity vs operating-point bias V_bias      -- memory peaks at V~0
  (e) NARMA-10 one-step prediction trace                  -- a nonlinear task
  (f) memory capacity vs ensemble size (devices / node)   -- the hardware knob

Mean-field = expected magnetisation (noise-free reference, like PBNN
``software`` mode). Stochastic = real telegraph sampling with an ensemble of
devices per node (the hardware-realistic, shot-noise-limited path).

Run from the repo root:

    python experiments/14_rc_prototype.py
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
    TelegraphParams, stationary_mean, relaxation_time)
from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout, nrmse, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402

PURPLE, RED, DEEP, GREEN, LILAC = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4"

P = TelegraphParams()           # Chapter 2.3 Device-A operating point
MAX_DELAY = 25

# Locked prototype configs (see experiments-suite tuning).
MF = dict(n_nodes=120, mode="meanfield", effective_spectral_radius=0.6,
          effective_input_scale=0.5, dt=8e-9, seed=1)
ST = dict(n_nodes=100, mode="stochastic", effective_spectral_radius=0.5,
          effective_input_scale=2.0, dt=25e-9, substeps=25, ensemble=96, seed=1)


def _mc(cfg_kw, u):
    res = SMTJReservoir(ReservoirConfig(**cfg_kw), n_inputs=1)
    X = res.run(u, washout=100)
    return memory_capacity(X, u[100:], max_delay=MAX_DELAY)


def main() -> None:
    t_start = time.time()
    u_mc = tasks.memory_capacity_inputs(1200, seed=2)

    # (c) forgetting curves -------------------------------------------------#
    mc_mf, per_mf = _mc(MF, u_mc)
    mc_st, per_st = _mc(ST, u_mc)
    print(f"Memory capacity  : mean-field {mc_mf:5.2f} | "
          f"stochastic {mc_st:5.2f} (ensemble={ST['ensemble']})")

    # (d) MC vs operating-point bias (mean-field) ---------------------------#
    biases = np.array([0.0, 0.02, 0.05, 0.08, 0.12, 0.18])
    mc_vs_bias = []
    for vb in biases:
        m, _ = _mc({**MF, "V_bias": float(vb)}, u_mc)
        mc_vs_bias.append(m)
    mc_vs_bias = np.array(mc_vs_bias)

    # (e) NARMA-10 prediction (stochastic) ----------------------------------#
    u_n, y_n = tasks.narma10(1800, seed=3)
    res = SMTJReservoir(ReservoirConfig(**ST), n_inputs=1)
    Xn = res.run(u_n, washout=200)
    y_al = y_n[200:]
    n_tr = 1200
    ro = RidgeReadout(alpha=1e-3).fit(Xn[:n_tr], y_al[:n_tr])
    pred = ro.predict(Xn[n_tr:])
    narma_nrmse = nrmse(y_al[n_tr:], pred)
    print(f"NARMA-10 NRMSE   : stochastic {narma_nrmse:.3f}")

    # (f) MC vs ensemble size (stochastic) ----------------------------------#
    ensembles = [8, 24, 64, 128]
    mc_vs_ens = []
    for e in ensembles:
        m, _ = _mc({**ST, "ensemble": e}, u_mc)
        mc_vs_ens.append(m)
    mc_vs_ens = np.array(mc_vs_ens)

    # ----------------------------- figure ----------------------------------#
    fig, ax = plt.subplots(2, 3, figsize=(16, 9))

    # (a) transfer
    V = np.linspace(-0.3, 0.3, 200)
    ax[0, 0].plot(V * 1e3, stationary_mean(V, Delta=P.Delta, V_c0=P.V_c0),
                  color=PURPLE, lw=2.2)
    ax[0, 0].axhline(0, color="grey", lw=0.6)
    ax[0, 0].axvline(0, color="grey", lw=0.6)
    ax[0, 0].set_xlabel("bias V (mV)")
    ax[0, 0].set_ylabel(r"$\langle s\rangle_\infty = \tanh(\Delta V / V_{c0})$")
    ax[0, 0].set_title("Device transfer (nonlinearity)")
    ax[0, 0].grid(alpha=0.3)

    # (b) tau(V)
    tau = relaxation_time(V, tau_0=P.tau_0, Delta=P.Delta, V_c0=P.V_c0) * 1e9
    ax[0, 1].plot(V * 1e3, tau, color=RED, lw=2.2)
    ax[0, 1].set_xlabel("bias V (mV)")
    ax[0, 1].set_ylabel(r"$\tau(V) = 1/(r_\uparrow + r_\downarrow)$ (ns)")
    ax[0, 1].set_title(r"Correlation time (tunable memory)")
    ax[0, 1].grid(alpha=0.3)

    # (c) forgetting curve
    delays = np.arange(1, MAX_DELAY + 1)
    ax[0, 2].bar(delays - 0.2, per_mf, width=0.4, color=PURPLE,
                 label=f"mean-field (MC={mc_mf:.2f})")
    ax[0, 2].bar(delays + 0.2, per_st, width=0.4, color=LILAC,
                 label=f"stochastic (MC={mc_st:.2f})")
    ax[0, 2].set_xlabel("delay k (steps)")
    ax[0, 2].set_ylabel(r"recall $r^2$ of $u[t-k]$")
    ax[0, 2].set_title("Forgetting curve")
    ax[0, 2].legend(fontsize=9)
    ax[0, 2].grid(alpha=0.3, axis="y")

    # (d) MC vs bias
    ax[1, 0].plot(biases * 1e3, mc_vs_bias, "o-", color=DEEP, lw=2)
    ax[1, 0].set_xlabel(r"operating-point bias $V_{bias}$ (mV)")
    ax[1, 0].set_ylabel("memory capacity (mean-field)")
    ax[1, 0].set_title("Memory peaks near zero bias")
    ax[1, 0].grid(alpha=0.3)

    # (e) NARMA-10 trace
    show = slice(0, 200)
    ax[1, 1].plot(y_al[n_tr:][show], color="black", lw=1.6, label="target")
    ax[1, 1].plot(pred[show], color=RED, lw=1.2, ls="--", label="readout")
    ax[1, 1].set_xlabel("test step")
    ax[1, 1].set_ylabel("NARMA-10 output")
    ax[1, 1].set_title(f"NARMA-10 (NRMSE = {narma_nrmse:.2f})")
    ax[1, 1].legend(fontsize=9)
    ax[1, 1].grid(alpha=0.3)

    # (f) MC vs ensemble
    ax[1, 2].plot(ensembles, mc_vs_ens, "s-", color=GREEN, lw=2,
                  label="stochastic")
    ax[1, 2].axhline(mc_mf, color=PURPLE, ls=":", lw=1.8,
                     label=f"mean-field ideal ({mc_mf:.1f})")
    ax[1, 2].set_xlabel("ensemble size (devices / node)")
    ax[1, 2].set_ylabel("memory capacity")
    ax[1, 2].set_title("Shot-noise vs device count")
    ax[1, 2].legend(fontsize=9)
    ax[1, 2].grid(alpha=0.3)

    fig.suptitle("sMTJ reservoir-computing prototype "
                 "(same Chapter 2.3 device, run as a dynamical node)",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "14_rc_prototype.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    main()
