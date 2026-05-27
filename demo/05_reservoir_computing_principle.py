"""Demo 05: the principle of sMTJ reservoir computing.

A publication-quality explanatory figure. Top: the reservoir-computing pipeline
(input injection -> fixed random reservoir of superparamagnetic sMTJ nodes ->
trained linear readout), with the three defining properties annotated. Bottom,
from the actual simulator:

  (i)   the random-telegraph substrate -- real +/-1 sMTJ switching traces whose
        dwell time is the fading memory;
  (ii)  the reservoir response -- diverse analog node activations (high-dim,
        nonlinear projection of the input history);
  (iii) the trained readout reconstructing a delayed target from the reservoir
        state -- only these weights are learned.

Output: demo/figures/05_reservoir_computing_principle.png

Run:  python demo/05_reservoir_computing_principle.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.device.telegraph import TelegraphArray, TelegraphParams  # noqa: E402
from smtj_pbnn_sim.reservoir import (                                       # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout)


# Palette (shared with demo 01).
PURPLE_DARK, PURPLE_MED, PURPLE_LIGHT = "#4B1369", "#6E2C91", "#A97DBE"
RED, GREEN, GRAY, LIGHT = "#A82038", "#0E8A6F", "#6B7280", "#E5E7EB"


def _telegraph_traces():
    """Two real +/-1 sMTJ traces under a stepped bias (dwell-time tuning)."""
    arr = TelegraphArray(2, TelegraphParams(), seed=3)
    dt = 1.0e-9
    n = 600
    V = np.where(np.arange(n) < n // 2, 0.0, 0.08)   # low then higher bias
    s = np.empty((n, 2))
    for t in range(n):
        s[t] = arr.step(V[t], dt)
    return np.arange(n) * dt * 1e9, s, V          # time in ns


def _reservoir_signals():
    """Mean-field reservoir response + a trained readout of a delayed target."""
    rng = np.random.default_rng(0)
    n = 260
    # Structured input: piecewise sinusoid so the traces are legible.
    t = np.arange(n)
    u = 0.6 * np.sin(2 * np.pi * t / 23) + 0.4 * np.sin(2 * np.pi * t / 7)
    cfg = ReservoirConfig(n_nodes=60, mode="meanfield",
                          effective_spectral_radius=0.7,
                          effective_input_scale=1.0, dt=8e-9, seed=1)
    res = SMTJReservoir(cfg, 1)
    X = res.run(u, washout=40)
    u_al = u[40:]
    # Train a readout to recall u[t-4] (a fading-memory task).
    k = 4
    target = u_al[:-k]
    Xk = X[k:]
    n_tr = int(0.6 * len(target))
    ro = RidgeReadout(alpha=1e-6).fit(Xk[:n_tr], target[:n_tr])
    pred = ro.predict(Xk)
    return u_al, X, target, pred, k


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
    from matplotlib.gridspec import GridSpec

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 12,
        "savefig.bbox": "tight",
    })

    t_ns, s_tr, V_tr = _telegraph_traces()
    u_al, X, target, pred, k = _reservoir_signals()

    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(2, 3, height_ratios=[1.05, 1.0], hspace=0.32, wspace=0.28)

    # ===================== TOP: schematic =================================#
    axs = fig.add_subplot(gs[0, :])
    axs.set_xlim(0, 16)
    axs.set_ylim(0, 6)
    axs.axis("off")
    axs.text(8, 5.75, "Reservoir computing on stochastic sMTJ nodes",
             ha="center", va="center", fontsize=17, fontweight="bold",
             color=PURPLE_DARK)

    # input
    axs.add_patch(FancyBboxPatch((0.4, 2.4), 1.7, 1.2,
                  boxstyle="round,pad=0.05,rounding_size=0.12",
                  facecolor=LIGHT, edgecolor=PURPLE_DARK, lw=1.5))
    axs.text(1.25, 3.0, r"input" "\n" r"$u(t)$", ha="center", va="center",
             fontsize=13, color=PURPLE_DARK, fontweight="bold")

    # reservoir box
    axs.add_patch(FancyBboxPatch((3.3, 0.8), 7.2, 4.4,
                  boxstyle="round,pad=0.06,rounding_size=0.2",
                  facecolor="#F5F0F8", edgecolor=PURPLE_MED, lw=2))
    axs.text(6.9, 4.78, "fixed random reservoir  (NOT trained)",
             ha="center", va="center", fontsize=12.5, style="italic",
             color=PURPLE_MED)
    # nodes
    rng = np.random.default_rng(2)
    pos = np.column_stack([rng.uniform(3.9, 9.9, 12), rng.uniform(1.3, 4.2, 12)])
    for (x, y) in pos:
        axs.add_patch(Circle((x, y), 0.26, facecolor=PURPLE_LIGHT,
                             edgecolor=PURPLE_DARK, lw=1.2, zorder=3))
    # a few recurrent connections
    for _ in range(14):
        i, j = rng.integers(0, 12, 2)
        if i != j:
            axs.add_patch(FancyArrowPatch(pos[i], pos[j], arrowstyle="-|>",
                          mutation_scale=8, color=GRAY, lw=0.8, alpha=0.5,
                          connectionstyle="arc3,rad=0.25", zorder=2))
    axs.text(6.9, 0.5,
             r"N superparamagnetic sMTJ nodes  ·  fading memory $\tau(V)$  ·  "
             r"high-dim nonlinear projection",
             ha="center", va="center", fontsize=11, color=PURPLE_DARK)

    # readout box
    axs.add_patch(FancyBboxPatch((11.6, 2.0), 2.3, 2.0,
                  boxstyle="round,pad=0.05,rounding_size=0.12",
                  facecolor="#E8F5F1", edgecolor=GREEN, lw=2))
    axs.text(12.75, 3.45, "linear", ha="center", va="center", fontsize=12.5,
             color=GREEN, fontweight="bold")
    axs.text(12.75, 3.05, "readout", ha="center", va="center", fontsize=12.5,
             color=GREEN, fontweight="bold")
    axs.text(12.75, 2.55, r"$W_{out}$ (TRAINED)", ha="center", va="center",
             fontsize=10.5, color=GREEN)

    # output
    axs.text(15.4, 3.0, r"$\hat{y}(t)$", ha="center", va="center",
             fontsize=14, color=PURPLE_DARK, fontweight="bold")

    # arrows
    axs.add_patch(FancyArrowPatch((2.1, 3.0), (3.3, 3.0), arrowstyle="-|>",
                  mutation_scale=16, color=PURPLE_DARK, lw=1.6))
    axs.text(2.7, 3.25, r"$W_{in}$", ha="center", fontsize=10.5,
             color=PURPLE_DARK, style="italic")
    axs.add_patch(FancyArrowPatch((10.5, 3.0), (11.6, 3.0), arrowstyle="-|>",
                  mutation_scale=16, color=GREEN, lw=1.6))
    axs.add_patch(FancyArrowPatch((13.9, 3.0), (15.0, 3.0), arrowstyle="-|>",
                  mutation_scale=16, color=PURPLE_DARK, lw=1.6))
    axs.text(8.0, 1.0, "", ha="center")

    # ===================== BOTTOM-LEFT: telegraph substrate ===============#
    ax0 = fig.add_subplot(gs[1, 0])
    ax0.plot(t_ns, s_tr[:, 0] * 0.45 + 1.6, color=PURPLE_DARK, lw=0.9,
             drawstyle="steps-mid")
    ax0.plot(t_ns, s_tr[:, 1] * 0.45 - 0.1, color=PURPLE_MED, lw=0.9,
             drawstyle="steps-mid")
    ax0.axvline(t_ns[len(t_ns) // 2], color=RED, ls="--", lw=1.2)
    ax0.text(t_ns[len(t_ns) // 4], 2.45, "V = 0\n(slow, long dwell)",
             ha="center", fontsize=9, color=GRAY)
    ax0.text(t_ns[3 * len(t_ns) // 4], 2.45, "V > 0\n(biased)",
             ha="center", fontsize=9, color=GRAY)
    ax0.set_ylim(-0.9, 3.0)
    ax0.set_yticks([])
    ax0.set_xlabel("time (ns)")
    ax0.set_title("sMTJ telegraph substrate", fontsize=12)

    # ===================== BOTTOM-MID: reservoir response =================#
    ax1 = fig.add_subplot(gs[1, 1])
    offsets = np.linspace(0, 6, 6)
    idx = np.argsort(X.var(axis=0))[-6:]          # the 6 most active nodes
    for o, j in zip(offsets, idx):
        ax1.plot(X[:120, j] + o, color=PURPLE_MED, lw=1.1)
    ax1.set_yticks([])
    ax1.set_xlabel("reservoir step")
    ax1.set_title("Diverse node activations", fontsize=12)

    # ===================== BOTTOM-RIGHT: trained readout ==================#
    ax2 = fig.add_subplot(gs[1, 2])
    show = slice(0, 120)
    ax2.plot(target[show], color="black", lw=1.8, label=fr"target $u(t-{k})$")
    ax2.plot(pred[show], color=GREEN, lw=1.3, ls="--", label="readout")
    ax2.set_xlabel("reservoir step")
    ax2.set_title("Trained linear readout", fontsize=12)
    ax2.legend(fontsize=9, loc="upper right")
    ax2.grid(alpha=0.3)

    out = REPO / "demo" / "figures" / "05_reservoir_computing_principle.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    print(f"Saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
