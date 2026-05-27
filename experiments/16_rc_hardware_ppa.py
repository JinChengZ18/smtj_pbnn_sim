"""16 -- Hardware PPA evaluation of the sMTJ reservoir computer.

Puts the sMTJ reservoir on the same energy footing as experiment 13 and asks
the hardware question directly: against a conventional digital echo-state
network (ESN), what does running the reservoir in sMTJ physics buy?

The headline is structural: a digital ESN pays an O(N^2) dense recurrent
matrix-vector product every step, whereas the sMTJ reservoir realises the
recurrence in analog device dynamics at O(N x ensemble) cost. Four panels:

  (a) sMTJ-RC per-step energy breakdown
  (b) energy per inference: sMTJ-RC vs digital ESN (bracketed digital/CIM)
  (c) energy scaling vs reservoir size N -- O(N) vs O(N^2)
  (d) accuracy (memory capacity) vs energy -- the Pareto, sweeping device count

Energies reuse the Chapter-2.3 tech_params; the digital ESN is bracketed
between a conventional digital MAC (1 pJ, conservative) and an optimistic
in-array CIM lower bound. Accuracy is the noise-free mean-field reservoir
(the digital-equivalent of the same dynamics) vs the real stochastic device.

Run from the repo root:

    python experiments/16_rc_hardware_ppa.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.ppa import (                                    # noqa: E402
    default_28nm, ReservoirHW, smtj_rc_step_energy,
    smtj_rc_inference_energy, digital_esn_inference_energy)
from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402

PURPLE, RED, DEEP, GREEN, LILAC, GOLD = \
    "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4", "#D4A017"

TECH = default_28nm()
L = 1000                       # inference sequence length (steps)
N = 100                        # reservoir size for the head-to-head
DT = 25e-9
SUBSTEPS = 25


def _stochastic_mc(ensemble, u):
    cfg = ReservoirConfig(n_nodes=N, mode="stochastic",
                          effective_spectral_radius=0.5,
                          effective_input_scale=2.0, dt=DT,
                          substeps=SUBSTEPS, ensemble=ensemble, seed=1)
    X = SMTJReservoir(cfg, 1).run(u, washout=100)
    return memory_capacity(X, u[100:], max_delay=25)[0]


def main() -> None:
    t0 = time.time()
    u = tasks.memory_capacity_inputs(1100, seed=2)

    # (a) per-step breakdown -----------------------------------------------#
    hw = ReservoirHW(n_nodes=N, ensemble=96, dt=DT)
    bd = smtj_rc_step_energy(hw, TECH)

    # (b) per-inference comparison at N -------------------------------------#
    e_rc = smtj_rc_inference_energy(hw, TECH, L)
    e_dig = digital_esn_inference_energy(N, TECH, L, memory="sram_cim",
                                         digital_mac=True)
    e_cim = digital_esn_inference_energy(N, TECH, L, memory="sram_cim",
                                         digital_mac=False)
    e_mram = digital_esn_inference_energy(N, TECH, L, memory="stt_mram",
                                          digital_mac=True)
    bars = {"sMTJ-RC": e_rc, "digital ESN\n(SRAM, 1pJ MAC)": e_dig,
            "digital ESN\n(STT-MRAM)": e_mram, "CIM ESN\n(optimistic)": e_cim}

    # (c) scaling vs N ------------------------------------------------------#
    Ns = np.array([32, 64, 128, 256, 512, 1024, 2048])
    e_rc_N = np.array([smtj_rc_inference_energy(
        ReservoirHW(n_nodes=int(n), ensemble=96, dt=DT), TECH, L) for n in Ns])
    e_dig_N = np.array([digital_esn_inference_energy(
        int(n), TECH, L, digital_mac=True) for n in Ns])
    e_cim_N = np.array([digital_esn_inference_energy(
        int(n), TECH, L, digital_mac=False) for n in Ns])

    # (d) accuracy-energy Pareto -------------------------------------------#
    ensembles = [4, 16, 48, 128, 256]
    mc_pts, e_pts = [], []
    for e in ensembles:
        mc_pts.append(_stochastic_mc(e, u))
        e_pts.append(smtj_rc_inference_energy(
            ReservoirHW(n_nodes=N, ensemble=e, dt=DT), TECH, L))
    mc_pts = np.array(mc_pts)
    e_pts = np.array(e_pts)
    # Digital-equivalent accuracy = noise-free mean-field of the same dynamics.
    cfg_mf = ReservoirConfig(n_nodes=N, mode="meanfield",
                             effective_spectral_radius=0.5,
                             effective_input_scale=2.0, dt=DT, seed=1)
    mc_dig = memory_capacity(
        SMTJReservoir(cfg_mf, 1).run(u, washout=100), u[100:], max_delay=25)[0]

    print(f"sMTJ-RC inference ({L} steps, N={N}) = {e_rc*1e9:.1f} nJ")
    print(f"  vs digital ESN (1pJ MAC) {e_dig*1e9:.0f} nJ  "
          f"({e_dig/e_rc:.0f}x), CIM lower bound {e_cim*1e9:.1f} nJ")
    print(f"energy / MC-unit : sMTJ-RC {e_pts[-1]/mc_pts[-1]*1e9:.0f} nJ  "
          f"vs digital {e_dig/mc_dig*1e9:.0f} nJ")

    # ----------------------------- figure ---------------------------------#
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    # (a)
    keys = list(bd.keys())
    vals = [bd[k] * 1e12 for k in keys]
    ax[0, 0].bar(keys, vals, color=[RED, PURPLE, DEEP, GREEN], edgecolor="black")
    for i, v in enumerate(vals):
        ax[0, 0].text(i, v * 1.05, f"{v:.1f} pJ", ha="center", fontsize=10)
    ax[0, 0].set_yscale("log")
    ax[0, 0].set_ylabel("energy per step (pJ)")
    ax[0, 0].set_title(f"sMTJ-RC per-step breakdown (N={N}, ens=96)")
    ax[0, 0].grid(axis="y", alpha=0.3, which="both")

    # (b)
    bk = list(bars.keys())
    bv = [bars[k] * 1e9 for k in bk]
    colors_b = [RED, PURPLE, DEEP, LILAC]
    ax[0, 1].bar(bk, bv, color=colors_b, edgecolor="black")
    for i, v in enumerate(bv):
        ax[0, 1].text(i, v * 1.15, f"{v:.0f} nJ" if v >= 1 else f"{v*1e3:.0f} pJ",
                      ha="center", fontsize=9)
    ax[0, 1].set_yscale("log")
    ax[0, 1].set_ylabel("energy per inference (nJ)")
    ax[0, 1].set_title(f"Energy per inference ({L} steps, N={N})")
    ax[0, 1].tick_params(axis="x", labelsize=8)
    ax[0, 1].grid(axis="y", alpha=0.3, which="both")

    # (c)
    ax[1, 0].loglog(Ns, e_rc_N * 1e9, "o-", color=RED, lw=2, label="sMTJ-RC  O(N)")
    ax[1, 0].loglog(Ns, e_dig_N * 1e9, "s-", color=PURPLE, lw=2,
                    label="digital ESN  O(N$^2$)")
    ax[1, 0].loglog(Ns, e_cim_N * 1e9, "^--", color=LILAC, lw=1.6,
                    label="CIM ESN (optimistic)")
    ax[1, 0].set_xlabel("reservoir size N")
    ax[1, 0].set_ylabel("energy per inference (nJ)")
    ax[1, 0].set_title("Energy scaling: analog physics vs dense matmul")
    ax[1, 0].legend(fontsize=9)
    ax[1, 0].grid(alpha=0.3, which="both")

    # (d)
    ax[1, 1].plot(e_pts * 1e9, mc_pts, "o-", color=RED, lw=2, zorder=3,
                  label="sMTJ-RC (sweep ensemble)")
    for e, m, ens in zip(e_pts, mc_pts, ensembles):
        ax[1, 1].annotate(f"{ens}", (e * 1e9, m), fontsize=8,
                          textcoords="offset points", xytext=(4, 5))
    ax[1, 1].scatter([e_dig * 1e9], [mc_dig], color=PURPLE, s=110, marker="s",
                     edgecolor="black", zorder=3, label="digital ESN (same N)")
    ax[1, 1].set_xscale("log")
    ax[1, 1].set_xlabel("energy per inference (nJ)")
    ax[1, 1].set_ylabel("memory capacity")
    ax[1, 1].set_title("Accuracy-energy tradeoff (label = devices/node)")
    ax[1, 1].legend(fontsize=9)
    ax[1, 1].grid(alpha=0.3, which="both")

    fig.suptitle("Hardware PPA evaluation of the sMTJ reservoir computer",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "16_rc_hardware_ppa.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
