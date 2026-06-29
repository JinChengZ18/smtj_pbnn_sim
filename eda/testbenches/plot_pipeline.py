#!/usr/bin/env python3
"""Operating-mode pipeline / phase-timing diagram (Chapter 4, fig 4.21).

Two time-multiplexed operating modes of the shared sMTJ array and their phase pipeline:
(a) p-bit inference -- one decision = T Bernoulli samples, each a write (Phi_W) -> settle -> read
    (Phi_R) cycle; the T reads are averaged to recover E[s] (confidence early-exit shortens T).
(b) reservoir processing -- load inputs (write) -> low-barrier free stochastic evolution ->
    column-shared SAR read-out that time-multiplexes the M columns through one converter.

The phase clocking is shown HONESTLY: instead of a free-running decorative clock, the two
phase-enable waveforms Phi_W and Phi_R are drawn aligned to the sample boxes -- Phi_W is high
exactly over each write box, Phi_R high exactly over each read box -- so the waveform IS the
per-sample timing, with light guides tying the edges to the phase boundaries of sample 1.

Run with Windows Python (matplotlib). Outputs article/figs/Chapter04_local_20.{png,svg,pdf}.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path

FIGS = Path(__file__).resolve().parent.parent.parent / "article" / "figs"
WR, RD, SET, OUT, EDGE = "#c0392b", "#2c5aa0", "#9aa0a6", "#3f7a4a", "#333333"
TXT, MUT = "#1a1a1a", "#555555"
PHI_W, PHI_R = r"$\Phi_\mathrm{W}$", r"$\Phi_\mathrm{R}$"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def box(ax, x, y, w, h, c, label, tc="white", fs=9):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=c, edgecolor=EDGE, lw=1.1))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color=tc, fontsize=fs)


def waveform(ax, x0, x1, ylo, h, highs, label, color):
    """Digital phase-enable waveform: low at ylo, high at ylo+h over the `highs` intervals."""
    yhi = ylo + h
    xs, ys = [x0], [ylo]
    for a, b in highs:
        xs += [a, a, b, b]
        ys += [ylo, yhi, yhi, ylo]
    xs += [x1]; ys += [ylo]
    ax.plot(xs, ys, color=color, lw=1.6, solid_joinstyle="miter", clip_on=False)
    ax.text(x0 - 0.25, ylo + h / 2, label, ha="right", va="center", fontsize=9.5, color=color)


def main():
    fig, ax = plt.subplots(figsize=(13.0, 5.6))
    ax.set_xlim(0, 27); ax.set_ylim(0, 11.4); ax.axis("off")

    # ---- (a) p-bit inference lane ----
    ax.text(0, 10.7, "(a)  p-bit inference   —   one decision = T Bernoulli samples", fontsize=11.5,
            color=TXT, fontweight="bold")

    y = 6.7                                   # sample-box row
    starts = (0.6, 5.0, 9.4)
    w_wr, w_set, w_rd = 1.5, 0.9, 1.5
    write_hi = [(x0, x0 + w_wr) for x0 in starts]
    read_hi = [(x0 + w_wr + w_set, x0 + w_wr + w_set + w_rd) for x0 in starts]
    xend = 13.3
    # phase-enable waveforms, aligned to the boxes below (this replaces the old free clock)
    waveform(ax, 0.6, xend, 9.7, 0.7, write_hi, PHI_W, WR)
    waveform(ax, 0.6, xend, 8.6, 0.7, read_hi, PHI_R, RD)
    ax.text(0.6, 8.15, "phase enables high over the matching phase below (one sample shown gated)",
            fontsize=7.6, color=MUT)

    for k, x0 in enumerate(starts):
        box(ax, x0, y, w_wr, 1.0, WR, PHI_W + "\nwrite")
        box(ax, x0 + w_wr, y, w_set, 1.0, SET, "relax", fs=8)
        box(ax, x0 + w_wr + w_set, y, w_rd, 1.0, RD, PHI_R + "\nread")
        ax.text(x0 + 1.95, y - 0.35, f"sample {k+1}", ha="center", fontsize=8, color=TXT)
    # light guides tying sample-1 waveform edges to the phase boundaries
    for gx in (0.6, 0.6 + w_wr, 0.6 + w_wr + w_set, 0.6 + w_wr + w_set + w_rd):
        ax.plot([gx, gx], [y + 1.0, 9.7], color="#bbbbbb", lw=0.7, ls=":", zorder=0)

    ax.text(13.9, y + 0.5, "···  × T", ha="center", va="center", fontsize=12, color=TXT)
    box(ax, 15.6, y, 2.4, 1.0, OUT, "average\n" + r"$\Sigma/T$")
    ax.annotate("", xy=(20.6, y + 0.5), xytext=(18.0, y + 0.5),
                arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.6))
    ax.text(21.0, y + 0.5, r"$\approx \mathbb{E}[s]$", ha="left", va="center", fontsize=13,
            color=TXT, fontweight="bold")
    ax.text(0.6, y - 0.95, "WWL/BL write driver active in " + PHI_W + ";  RWL/RBL + StrongARM active in "
            + PHI_R + ";  confidence early-exit shortens T", fontsize=8, color=MUT)

    # ---- (b) reservoir processing lane ----
    ax.text(0, 4.2, "(b)  reservoir processing   —   column-shared, time-multiplexed read-out",
            fontsize=11.5, color=TXT, fontweight="bold")
    yb = 2.2
    box(ax, 0.6, yb, 2.6, 1.0, WR, "load inputs\n(write)")
    box(ax, 3.6, yb, 5.0, 1.0, SET, "free stochastic\nevolution  (low " + r"$\Delta$" + ")", tc=TXT, fs=9)
    x0 = 9.0; slot = 1.45
    for j in range(5):
        box(ax, x0 + j * slot, yb, slot - 0.08, 1.0, RD, f"col {j+1}" if j < 4 else "col M", fs=8)
    ax.text(x0 + 2.5 * slot, yb + 1.35, "1 SAR  ·  time-multiplexed over M columns", ha="center",
            fontsize=8.5, color=TXT)
    ax.annotate("", xy=(18.2, yb + 0.5), xytext=(16.4, yb + 0.5),
                arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.6))
    ax.text(18.5, yb + 0.5, "read-out vector", ha="left", va="center", fontsize=10, color=TXT)
    ax.text(0.6, yb - 0.6, "low " + r"$\Delta$" + " raises C2C noise for rich dynamics;  conflicts with "
            "p-bit write-retention → modes are time-exclusive on one array", fontsize=8, color=MUT)

    # legend
    lx = 0.6
    for c, t in ((WR, PHI_W + "  write / load"), (SET, "settle / evolve"), (RD, PHI_R + "  read"),
                 (OUT, "accumulate / average")):
        ax.add_patch(Rectangle((lx, 0.35), 0.5, 0.4, facecolor=c, edgecolor=EDGE, lw=1))
        ax.text(lx + 0.65, 0.55, t, va="center", fontsize=8.5, color=TXT); lx += 5.4

    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIGS / f"Chapter04_local_20.{ext}", dpi=200, bbox_inches="tight")
    print("wrote Chapter04_local_20.{png,svg,pdf}")


if __name__ == "__main__":
    main()
