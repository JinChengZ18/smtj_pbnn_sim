#!/usr/bin/env python3
"""Operating-mode pipeline / timing diagram for the supplement (fig 12).

Shows the two time-multiplexed operating modes of the shared sMTJ array and their phase pipeline:
(a) p-bit inference -- one decision = T Bernoulli samples, each a write (Φ_w) -> settle -> read
    (Φ_r) cycle; the T reads are averaged to recover E[s] (confidence early-exit shortens T).
(b) reservoir processing -- load inputs (write) -> low-barrier free stochastic evolution ->
    column-shared SAR read-out that time-multiplexes the M columns through one converter.
The two modes are mutually exclusive in time on the same physical array (see dual-mode section).
Run with Windows Python (matplotlib). Outputs article/figs/Supplement_local_12.{png,svg,pdf}.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow
from pathlib import Path

FIGS = Path(__file__).resolve().parent.parent.parent / "article" / "figs"
WR, RD, SET, OUT, EDGE = "#c0392b", "#2c5aa0", "#9aa0a6", "#3f7a4a", "#333333"
TXT = "#1a1a1a"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def box(ax, x, y, w, h, c, label, tc="white", fs=9):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=c, edgecolor=EDGE, lw=1.1))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", color=tc, fontsize=fs)


def main():
    fig, ax = plt.subplots(figsize=(13.0, 5.0))
    ax.set_xlim(0, 27); ax.set_ylim(0, 10); ax.axis("off")

    # CLK reference strip
    ax.text(-0.2, 9.3, "CLK", ha="right", va="center", fontsize=9, color=TXT)
    x = 0.6; up = True
    while x < 26:
        ax.plot([x, x, x + 0.5], [9.1 if up else 9.5, 9.5 if up else 9.1, 9.5 if up else 9.1],
                color="#777", lw=1.0)
        x += 0.5; up = not up

    # ---- (a) p-bit inference lane ----
    ax.text(0, 8.3, "(a)  p-bit inference   —   one decision = T Bernoulli samples", fontsize=11.5,
            color=TXT, fontweight="bold")
    y = 6.6
    for k, x0 in enumerate((0.6, 5.0, 9.4)):
        box(ax, x0, y, 1.5, 1.0, WR, "Φ_w\nwrite")
        box(ax, x0 + 1.5, y, 0.9, 1.0, SET, "relax", fs=8)
        box(ax, x0 + 2.4, y, 1.5, 1.0, RD, "Φ_r\nread")
        ax.text(x0 + 1.95, y - 0.35, f"sample {k+1}", ha="center", fontsize=8, color=TXT)
    ax.text(13.9, y + 0.5, "···  × T", ha="center", va="center", fontsize=12, color=TXT)
    box(ax, 15.6, y, 2.4, 1.0, OUT, "average\nΣ/T")
    ax.annotate("", xy=(20.6, y + 0.5), xytext=(18.0, y + 0.5),
                arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.6))
    ax.text(21.0, y + 0.5, "≈ E[s]", ha="left", va="center", fontsize=12, color=TXT, fontweight="bold")
    ax.text(0.6, y - 0.95, "WWL/BL write driver active in Φ_w;  RWL/RBL + StrongARM active in Φ_r;  "
            "confidence early-exit shortens T", fontsize=8, color="#555")

    # ---- (b) reservoir processing lane ----
    ax.text(0, 4.1, "(b)  reservoir processing   —   column-shared, time-multiplexed read-out",
            fontsize=11.5, color=TXT, fontweight="bold")
    yb = 2.2
    box(ax, 0.6, yb, 2.6, 1.0, WR, "load inputs\n(write)")
    box(ax, 3.6, yb, 5.0, 1.0, SET, "free stochastic\nevolution  (low Δ)", tc=TXT, fs=9)
    # column-shared SAR scan: M sub-slots through one converter
    x0 = 9.0; slot = 1.45
    for j in range(5):
        box(ax, x0 + j * slot, yb, slot - 0.08, 1.0, RD, f"col {j+1}" if j < 4 else "col M", fs=8)
    ax.text(x0 + 2.5 * slot, yb + 1.35, "1 SAR  ·  time-multiplexed over M columns", ha="center",
            fontsize=8.5, color=TXT)
    ax.annotate("", xy=(18.2, yb + 0.5), xytext=(16.4, yb + 0.5),
                arrowprops=dict(arrowstyle="-|>", color=EDGE, lw=1.6))
    ax.text(18.5, yb + 0.5, "read-out vector", ha="left", va="center", fontsize=10, color=TXT)
    ax.text(0.6, yb - 0.6, "low Δ raises C2C noise for rich dynamics;  conflicts with p-bit write-"
            "retention → modes are time-exclusive on one array", fontsize=8, color="#555")

    # legend
    lx = 0.6
    for c, t in ((WR, "Φ_w  write / load"), (SET, "settle / evolve"), (RD, "Φ_r  read"),
                 (OUT, "accumulate / average")):
        ax.add_patch(Rectangle((lx, 0.35), 0.5, 0.4, facecolor=c, edgecolor=EDGE, lw=1))
        ax.text(lx + 0.65, 0.55, t, va="center", fontsize=8.5, color=TXT); lx += 5.4

    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIGS / f"Supplement_local_12.{ext}", dpi=200, bbox_inches="tight")
    print("wrote Supplement_local_12.{png,svg,pdf}")


if __name__ == "__main__":
    main()
