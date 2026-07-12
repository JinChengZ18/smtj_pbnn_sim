#!/usr/bin/env python3
"""T3-5 figure: deterministic-replay column co-simulation panels.

Reads the per-trial arrays saved by replay_column_cosim.py
(_replay_trials_os0.npz / _replay_trials_os9.npz) and renders the raw
two-panel figure (numbering/letters live in the deck, not here).

Run (Windows or WSL): python eda/hero/plot_replay_cosim.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

plt.rcParams.update({"font.family": "Arial", "font.size": 13,
                     "axes.labelsize": 14, "axes.titlesize": 14})

summ = json.loads((HERE / "replay_column_cosim_summary.json")
                  .read_text(encoding="utf-8"))
d0 = np.load(HERE / "_replay_trials_os0.npz")
theta1 = summ["theta_plus_1"]
v0 = summ["variants"]["os0"]

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))

ax = axes[0]
pc, pca = d0["pc"], d0["pc_analog"]
jitter = (np.random.default_rng(7).uniform(-0.25, 0.25, len(pc)))
ax.plot([pc.min() - 2, pc.max() + 2], [pc.min() - 2, pc.max() + 2],
        color="0.6", lw=1.2, label="ideal mapping")
xs = np.array([pc.min() - 2, pc.max() + 2])
ax.plot(xs, v0["slope_fit"] * xs + v0["intercept_fit"], color="tab:red",
        lw=1.8, ls="--",
        label=f"fit: slope {v0['slope_fit']:.2f} (line-IR compression)")
ax.plot(pc + jitter, pca, "o", ms=3.5, alpha=0.45, color="tab:blue",
        mec="none")
ax.axvline(theta1, color="tab:green", lw=1.2, ls=":")
ax.text(theta1 + 0.4, pca.min(), "decision\nthreshold", fontsize=10,
        color="tab:green", va="bottom")
ax.set_xlabel("exact popcount (drawn column state)")
ax.set_ylabel("analog popcount at the sense node")
ax.set_title("replayed column: analog vs exact popcount")
ax.legend(fontsize=10, loc="upper left")

ax = axes[1]
resid = pca - pc
ax.hist(resid, bins=31, color="tab:blue", alpha=0.75)
ax.axvline(float(np.mean(resid)), color="tab:red", lw=1.8, ls="--")
ax.set_xlabel("analog - exact popcount residual")
ax.set_ylabel("trials")
ax.set_title("readout-chain residual (600 replays)")
txt = (f"agree {v0['n_agree']}/{v0['n_trials']}"
       f" (recal {v0['n_agree_recal']}/{v0['n_recal_eval']})\n"
       f"SA faithfulness {v0['sa_faithfulness']:.3f}\n"
       f"KS p = {v0['ks_p']:.2f}\n"
       f"far-end IR {v0['ir_far_end_mV_mean']:.1f} mV")
ax.text(0.97, 0.95, txt, transform=ax.transAxes, ha="right", va="top",
        fontsize=11,
        bbox=dict(boxstyle="round", fc="white", ec="0.7", alpha=0.9))

fig.tight_layout()
out = REPO / "figures" / "32_replay_column_cosim.png"
fig.savefig(out, dpi=200, bbox_inches="tight")
print(f"figure saved: {out}")
