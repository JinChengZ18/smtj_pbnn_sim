#!/usr/bin/env python3
"""Cross-section schematic of the 2T SOT-sMTJ cell (MTJ plan L1).

Vertical stack (not to scale), matching cell2t.gds: sky130 FEOL FETs and
metal stack drawn as real layers; the SOT track + MTJ pillar between met2 and
met3 drawn as the declared-non-manufacturable abstract black box. English
text, Arial, no figure numbering (deck adds letters/numbers per figure norms).

Output: figures/cell2t_cross_section.{png,svg}
Run from the repo root:  python eda/gen_cell2t_cross_section.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

plt.rcParams.update({
    "font.family": "Arial", "font.size": 11,
    "mathtext.fontset": "custom", "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold",
    "svg.hashsalt": "cell2t",           # deterministic clip-path ids (repro)
})

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "figures"

C = {
    "sub":   "#e8e0d0",
    "diff":  "#c8e6c9",
    "poly":  "#ef9a9a",
    "li1":   "#b0bec5",
    "met1":  "#90caf9",
    "met2":  "#64b5f6",
    "met3":  "#1e88e5",
    "via":   "#546e7a",
    "sot":   "#ffcc80",
    "mtj":   "#ba68c8",
    "box":   "#9e9e9e",
}

fig, ax = plt.subplots(figsize=(8.6, 5.2))

def rect(x, y, w, h, color, label=None, lx=None, ly_=None, ec="black", lw=0.6,
         hatch=None, fs=10, style="normal"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor=ec,
                           linewidth=lw, hatch=hatch, zorder=2))
    if label:
        ax.text(lx if lx is not None else x + w / 2,
                ly_ if ly_ is not None else y + h / 2,
                label, ha="center", va="center", fontsize=fs, style=style, zorder=3)

# ---- substrate + FEOL ----
rect(0.0, 0.0, 10.0, 1.0, C["sub"], "p-substrate (sky130 FEOL)")
# write FET
rect(0.6, 1.0, 2.2, 0.28, C["diff"])
rect(1.35, 1.28, 0.7, 0.22, C["poly"], "G", fs=9)
ax.text(1.7, 0.72, "write FET  MW\n$W$=2.2 µm", ha="center", fontsize=9)
# read FET
rect(6.8, 1.0, 1.6, 0.28, C["diff"])
rect(7.35, 1.28, 0.5, 0.22, C["poly"], "G", fs=9)
ax.text(7.6, 0.72, "read FET  MR\n$W$=0.42 µm", ha="center", fontsize=9)

# ---- li1 / met1 ----
for x, w in [(0.7, 0.5), (2.1, 0.5), (6.9, 0.4), (8.0, 0.3)]:
    rect(x + 0.1, 1.28, w - 0.2, 0.22, C["via"])   # licon posts (diff -> li1)
    rect(x, 1.5, w, 0.18, C["li1"])
rect(0.7, 1.9, 0.5, 0.2, C["met1"])
rect(2.1, 1.9, 0.5, 0.2, C["met1"])
rect(6.9, 1.9, 0.4, 0.2, C["met1"])
rect(8.0, 1.9, 0.3, 0.2, C["met1"], "RBL", lx=8.55, ly_=2.0, fs=9)
for x, w in [(0.8, 0.3), (2.2, 0.3), (7.0, 0.2), (8.05, 0.2)]:
    rect(x, 1.68, w, 0.22, C["via"])
ax.text(0.35, 1.59, "li1", fontsize=9, ha="right")
ax.text(0.35, 2.0, "met1", fontsize=9, ha="right")

# ---- met2: WBL, BE1, BE2/SL ----
rect(0.7, 2.5, 0.5, 0.22, C["met2"], "WBL", lx=0.95, ly_=2.35, fs=9)
rect(2.1, 2.5, 0.9, 0.22, C["met2"], "BE$_1$", lx=2.55, ly_=2.32, fs=9)
rect(3.9, 2.5, 0.9, 0.22, C["met2"], "BE$_2$ / SL", lx=4.35, ly_=2.32, fs=9)
rect(6.9, 2.5, 0.5, 0.22, C["met2"])
for x in (0.85, 2.25, 7.0):
    rect(x, 2.1, 0.25, 0.4, C["via"])
ax.text(0.35, 2.61, "met2", fontsize=9, ha="right")

# ---- abstract black box: SOT track + MTJ pillar ----
rect(2.1, 2.72, 2.7, 0.25, C["sot"], "SOT track (W, 200 nm wide)", fs=9)
rect(3.28, 2.97, 0.44, 0.55, C["mtj"], "MTJ\npillar", fs=8)
ax.add_patch(Rectangle((2.0, 2.66), 2.9, 0.95, fill=False, edgecolor=C["box"],
                       linewidth=1.4, linestyle=(0, (4, 3)), zorder=4))
ax.text(3.5, 4.0, "abstract black box (SOT track + MTJ pillar) - declared non-manufacturable\n"
                  "(no MRAM module in any open PDK; annotation GDS layers 201/0, 200/0;\n"
                  "BE/TE pads are real met2/met3)",
        ha="center", fontsize=9, style="italic")

# ---- met3: TE / read line ----
rect(3.0, 3.52, 1.0, 0.24, C["met3"], "TE", lx=3.5, ly_=3.85, fs=9)
rect(4.0, 3.52, 3.2, 0.24, C["met3"], "read line (met3)", fs=9)
rect(6.9, 2.72, 0.5, 0.24, C["met2"])
# read-side stack: met2 -> via2 -> met3
rect(7.0, 2.96, 0.3, 0.56, C["via"])
rect(6.7, 3.52, 1.6, 0.24, C["met3"])
ax.text(0.35, 3.64, "met3", fontsize=9, ha="right")

# current-path arrows (write path follows the actual route: WBL down through
# MW, back up to BE1, along the SOT track to BE2/SL)
for p0, p1, rad in [((0.95, 2.55), (1.6, 1.15), 0.3),
                    ((1.8, 1.15), (2.45, 2.72), 0.3),
                    ((2.6, 2.85), (4.2, 2.85), -0.15)]:
    ax.add_patch(FancyArrowPatch(p0, p1, connectionstyle=f"arc3,rad={rad}",
                                 arrowstyle="->", mutation_scale=11,
                                 color="#b71c1c", lw=1.2, zorder=5))
ax.text(0.85, 3.35, "write current\n(WBL $\\to$ MW $\\to$ BE$_1$ $\\to$ SOT $\\to$ BE$_2$/SL)",
        fontsize=8, color="#b71c1c", ha="center")
ax.add_patch(FancyArrowPatch((3.5, 3.76), (6.9, 3.76), connectionstyle="arc3,rad=0.0",
                             arrowstyle="<-", mutation_scale=12, color="#1a237e", lw=1.3, zorder=5))
ax.text(5.6, 4.35, "read current (RBL $\\to$ MR $\\to$ TE $\\to$ MTJ $\\to$ SOT $\\to$ BE$_2$/SL)",
        fontsize=8, color="#1a237e", ha="center")

ax.set_xlim(-0.9, 10.2)
ax.set_ylim(0, 4.8)
ax.axis("off")
fig.tight_layout()
OUT.mkdir(exist_ok=True)
for ext in ("png", "svg"):
    fig.savefig(OUT / f"cell2t_cross_section.{ext}", dpi=300 if ext == "png" else None,
                bbox_inches="tight",
                metadata=({"Date": None} if ext == "svg" else None))
    print(f"saved figures/cell2t_cross_section.{ext}")
