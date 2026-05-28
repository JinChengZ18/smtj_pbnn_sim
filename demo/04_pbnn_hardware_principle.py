"""
Fig 4.1 -- sMTJ-PBNN hardware principle (top-journal layout).

Three coupled functional blocks plus a feedback loop on the same physical
sMTJ substrate:

  1. MRAM CIM weight array runs a deterministic XNOR-popcount column sum
     over the stochastic input vector x^(r).
  2. Probability mapping & stochastic write driver convert the column
     current into a write stimulus u for the device array.
  3. Stochastic MTJ sampling array converts u into a new state vector
     x^(r+1) via thermal-activation switching.

x^(r+1) feeds back as the next input; spatial / temporal averaging across
cycles delivers the approximated expectation E[s].

Output: article/figs/Chapter04_local_01.png (and a sibling .pdf).
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (
    Ellipse, FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle,
)
from matplotlib.path import Path as MplPath


INK = "#2E1F4D"
PURPLE = "#563A86"
PURPLE_MID = "#8467B1"
PURPLE_FILL = "#E9E2F3"
PURPLE_FAINT = "#F7F4FB"
PURPLE_MTJ = "#7E5BA0"
GRAY = "#55515B"


mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Liberation Serif", "serif"],
    "mathtext.fontset": "stix",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ----------------------------------------------------------------------------
# Drawing primitives
# ----------------------------------------------------------------------------
def rounded_block(ax, x, y, w, h, fill=PURPLE_FAINT, edge=PURPLE, lw=1.8):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        linewidth=lw, edgecolor=edge, facecolor=fill, zorder=1,
    ))


def small_box(ax, x, y, w, h, text, fontsize=13, fill=PURPLE_FILL, fontweight="normal"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.03,rounding_size=0.10",
        linewidth=1.4, edgecolor=PURPLE, facecolor=fill, zorder=2,
    ))
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center",
            fontsize=fontsize, color=INK,
            fontweight=fontweight, linespacing=1.25, zorder=3)


def arrow(ax, start, end, label=None, label_offset=(0.0, 0.30),
          label_size=14, lw=1.9):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=19,
        linewidth=lw, color=INK,
        shrinkA=2, shrinkB=2, zorder=3,
    ))
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=label_size, color=INK, style="italic", zorder=4)


def draw_mtj(ax, cx, cy, w=0.55, h=0.78, color=PURPLE_MTJ, ell_h=0.18):
    """3D cylinder MTJ glyph."""
    ax.add_patch(Rectangle(
        (cx - w / 2, cy - h / 2 + ell_h / 2), w, h - ell_h,
        facecolor=color, edgecolor=PURPLE, linewidth=1.1, zorder=5,
    ))
    ax.add_patch(Ellipse(
        (cx, cy + h / 2 - ell_h / 2), w, ell_h,
        facecolor=PURPLE_FILL, edgecolor=PURPLE, linewidth=1.1, zorder=6,
    ))
    ax.add_patch(Ellipse(
        (cx, cy - h / 2 + ell_h / 2), w, ell_h,
        facecolor=color, edgecolor=PURPLE, linewidth=1.1, zorder=5,
    ))


def draw_pulse(ax, cx, cy, w=0.65, h=0.55):
    pts = [
        (cx - w / 2,         cy - h / 3),
        (cx - w / 4 - 0.03,  cy - h / 3),
        (cx - w / 4 - 0.03,  cy + h / 3),
        (cx + w / 4 + 0.03,  cy + h / 3),
        (cx + w / 4 + 0.03,  cy - h / 3),
        (cx + w / 2,         cy - h / 3),
    ]
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=INK, linewidth=1.7, zorder=4)


def draw_squiggle(ax, x0, y0, dx=0.72, amp=0.10, cycles=3):
    xs = np.linspace(x0, x0 + dx, 90)
    ys = y0 + amp * np.sin((xs - x0) / dx * cycles * 2 * np.pi)
    ax.plot(xs, ys, color=INK, linewidth=1.5, zorder=4)


# ----------------------------------------------------------------------------
# Figure
# ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(16, 9))
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")
ax.set_aspect("equal", adjustable="box")


# ---- Shared top-row block geometry ----
BLOCK_Y, BLOCK_TOP = 2.95, 8.85
BLOCK_H = BLOCK_TOP - BLOCK_Y   # 5.90


# ===== Stochastic Input Vector (vertically centred with the top blocks) =====
INPUT_X, INPUT_Y, INPUT_W, INPUT_H = 0.20, 3.95, 1.70, 4.20
small_box(ax, INPUT_X, INPUT_Y, INPUT_W, INPUT_H,
          "Stochastic\nInput\nVector\n\n$\\mathbf{x}^{(r)}$",
          fontsize=15.5, fontweight="bold")
arrow(ax, (INPUT_X + INPUT_W, 6.10), (2.30, 6.10), lw=1.9)


# ===== MRAM CIM Weight Array =====
MRAM_X, MRAM_W = 2.30, 5.90
rounded_block(ax, MRAM_X, BLOCK_Y, MRAM_W, BLOCK_H)
ax.text(MRAM_X + MRAM_W / 2, 8.55, "MRAM CIM Weight Array",
        ha="center", va="top", fontsize=18, color=INK,
        fontweight="bold", zorder=3)
ax.text(MRAM_X + MRAM_W / 2, 8.15, "(Deterministic Computation)",
        ha="center", va="top", fontsize=13.5, color=INK,
        style="italic", zorder=3)

# Crossbar geometry — explicit row/col positions
COLS = 4
ROWS = 4
xb_col_xs = np.linspace(MRAM_X + 1.45, MRAM_X + MRAM_W - 0.55, COLS)
xb_row_ys = np.array([6.85, 6.00, 5.15, 4.30])
MTJ_W_XB, MTJ_H_XB = 0.50, 0.66

# WL rows
for i, ry in enumerate(xb_row_ys):
    ax.add_patch(Rectangle(
        (MRAM_X - 0.05, ry - 0.20), 0.36, 0.40,
        facecolor=PURPLE_MID, edgecolor=PURPLE, linewidth=1.1, zorder=6,
    ))
    ax.plot([MRAM_X + 0.31, xb_col_xs[-1] + 0.42], [ry, ry],
            color=GRAY, linewidth=1.0, zorder=3)
    idx = f"{i}" if i < ROWS - 1 else "i"
    ax.text(MRAM_X + 0.52, ry + 0.34, f"WL$_{{{idx}}}$",
            fontsize=13.5, color=INK, ha="left", va="bottom", zorder=4)

# BL / RL labels
for j, cx in enumerate(xb_col_xs):
    ax.plot([cx, cx], [xb_row_ys[-1] - 0.40, xb_row_ys[0] + 0.45],
            color=GRAY, linewidth=1.0, zorder=3)
    jdx = f"{j}" if j < COLS - 1 else "j"
    ax.text(cx, 7.70, f"BL$_{{{jdx}}}$",
            fontsize=14, color=INK, ha="center", va="bottom", zorder=4)
    ax.text(cx + 0.13, 7.36, f"$RL_{{{jdx}}}$",
            fontsize=11.5, color=GRAY, style="italic",
            ha="left", va="bottom", zorder=4)

# MTJs at intersections with W_ij labels
for i, ry in enumerate(xb_row_ys):
    for j, cx in enumerate(xb_col_xs):
        draw_mtj(ax, cx, ry, w=MTJ_W_XB, h=MTJ_H_XB)
        idx = f"{i}" if i < ROWS - 1 else "i"
        jdx = f"{j}" if j < COLS - 1 else "j"
        ax.text(cx, ry, f"$W_{{{idx}{jdx}}}$",
                fontsize=10, color="white", ha="center", va="center",
                fontweight="bold", zorder=8)

# Inter-column ellipsis (between cols 2 and 3 of the visible four)
ell_col_x = (xb_col_xs[-2] + xb_col_xs[-1]) / 2
for ry in xb_row_ys:
    ax.text(ell_col_x, ry, r"$\cdots$",
            fontsize=15, color=INK, ha="center", va="center", zorder=4)

# Inter-row ellipsis (between WL_2 and WL_i)
ell_row_y = (xb_row_ys[-2] + xb_row_ys[-1]) / 2
ax.text(MRAM_X + 0.13, ell_row_y, r"$\vdots$",
        fontsize=16, color=INK, ha="center", va="center", zorder=4)
for cx in xb_col_xs:
    ax.text(cx, ell_row_y, r"$\vdots$",
            fontsize=14, color=INK, ha="center", va="center", zorder=4)

# Bottom column-current arrows
ARROW_TOP_Y, ARROW_BOT_Y = 3.85, 3.40
for cx in xb_col_xs:
    ax.annotate("", xy=(cx, ARROW_BOT_Y), xytext=(cx, ARROW_TOP_Y),
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.2),
                zorder=3)

# Bottom labels
ax.text(MRAM_X + 0.15, 3.65, "Analog Currents",
        fontsize=12.5, color=INK, style="italic",
        ha="left", va="center", zorder=4)
for j in range(min(3, COLS)):
    ax.text(xb_col_xs[j] + 0.17, 3.36, f"$I_{{\\mathrm{{col}},{j}}}$",
            fontsize=12, color=INK, ha="left", va="center", zorder=4)
ax.text(xb_col_xs[3] + 0.10, 3.36, r"$\cdots$",
        fontsize=15, color=INK, ha="left", va="center", zorder=4)

ax.text(MRAM_X + MRAM_W / 2, 3.08,
        r"$I_{\mathrm{col}}\propto\sum\mathrm{XNOR}(x,w)$"
        r"          KCL Summation",
        fontsize=13, color=INK, style="italic",
        ha="center", va="center", zorder=4)


# CIM -> Mapping arrow
arrow(ax, (MRAM_X + MRAM_W, 6.05), (8.45, 6.05),
      label="$I_{\\mathrm{col}}$", label_offset=(0, 0.32),
      label_size=15)


# ===== Probability Mapping & Stochastic Write Driver =====
MAP_X, MAP_W = 8.45, 3.05
rounded_block(ax, MAP_X, BLOCK_Y, MAP_W, BLOCK_H)
# Three-line title at explicit y positions
ax.text(MAP_X + MAP_W / 2, 8.55, "Probability Mapping",
        ha="center", va="top", fontsize=16, color=INK,
        fontweight="bold", zorder=3)
ax.text(MAP_X + MAP_W / 2, 8.18, "&",
        ha="center", va="top", fontsize=16, color=INK,
        fontweight="bold", zorder=3)
ax.text(MAP_X + MAP_W / 2, 7.85, "Stochastic Write Driver",
        ha="center", va="top", fontsize=16, color=INK,
        fontweight="bold", zorder=3)

# p = g(a) sub-box
small_box(ax, MAP_X + 0.20, 5.85, MAP_W - 0.40, 1.40,
          "$p = g(a)$\n(Nonlinear Mapping)", fontsize=13.5)
arrow(ax, (MAP_X + MAP_W / 2, 5.83), (MAP_X + MAP_W / 2, 4.80), lw=1.6)
# (u) Generator sub-box
small_box(ax, MAP_X + 0.20, 3.40, MAP_W - 0.40, 1.40,
          "($u$) Generator\nWrite Stimulus", fontsize=13.5)


# Mapping -> MTJ arrow (labeled u)
arrow(ax, (MAP_X + MAP_W, 4.10), (MAP_X + MAP_W + 0.25, 4.10),
      label="$u$", label_offset=(0, 0.32),
      label_size=15)


# ===== Stochastic MTJ Sampling Array =====
MTJ_X, MTJ_W = MAP_X + MAP_W + 0.25, 4.25
rounded_block(ax, MTJ_X, BLOCK_Y, MTJ_W, BLOCK_H)
ax.text(MTJ_X + MTJ_W / 2, 8.55, "Stochastic MTJ",
        ha="center", va="top", fontsize=17, color=INK,
        fontweight="bold", zorder=3)
ax.text(MTJ_X + MTJ_W / 2, 8.18, "Sampling Array",
        ha="center", va="top", fontsize=17, color=INK,
        fontweight="bold", zorder=3)
ax.text(MTJ_X + MTJ_W / 2, 7.75, "(Thermal Switching)",
        ha="center", va="top", fontsize=13.5, color=INK,
        style="italic", zorder=3)

# "Write pulses" caption
ax.text(MTJ_X + 0.25, 7.20, "Write pulses",
        fontsize=13, color=INK, ha="left", va="center", zorder=4)

# Top MTJ row
mtj_top_y = 6.45
draw_pulse(ax, MTJ_X + 0.55, mtj_top_y + 0.08, w=0.65, h=0.55)
draw_mtj(ax, MTJ_X + 1.45, mtj_top_y, w=0.62, h=0.90)
ax.text(MTJ_X + 1.85, mtj_top_y + 0.05, "MTJ",
        fontsize=13.5, color=INK, ha="left", va="center", zorder=5)
draw_squiggle(ax, MTJ_X + 2.55, mtj_top_y + 0.22)
draw_squiggle(ax, MTJ_X + 2.55, mtj_top_y - 0.04)

# Bottom MTJ row
mtj_bot_y = 4.25
draw_pulse(ax, MTJ_X + 0.55, mtj_bot_y + 0.08, w=0.65, h=0.55)
draw_mtj(ax, MTJ_X + 1.45, mtj_bot_y, w=0.62, h=0.90)
ax.text(MTJ_X + 1.85, mtj_bot_y + 0.05, "MTJ",
        fontsize=13.5, color=INK, ha="left", va="center", zorder=5)
draw_squiggle(ax, MTJ_X + 2.55, mtj_bot_y + 0.22)
draw_squiggle(ax, MTJ_X + 2.55, mtj_bot_y - 0.04)

# Vertical ellipses between top and bottom rows
mid_y = (mtj_top_y + mtj_bot_y) / 2
ax.text(MTJ_X + 0.55, mid_y, r"$\vdots$",
        fontsize=20, color=INK, ha="center", va="center", zorder=4)
ax.text(MTJ_X + 1.45, mid_y, r"$\vdots$",
        fontsize=20, color=INK, ha="center", va="center", zorder=4)

# "Thermal Fluctuations & Probabilistic Flip" caption on the right
ax.text(MTJ_X + 3.55, mid_y,
        "Thermal\nFluctuations\n&\nProbabilistic\nFlip",
        fontsize=12.5, color=INK, ha="center", va="center",
        linespacing=1.20, zorder=4)


# ===== New Stochastic State Vector =====
NSV_X, NSV_Y, NSV_W, NSV_H = 11.55, 1.50, 4.35, 1.15
small_box(ax, NSV_X, NSV_Y, NSV_W, NSV_H,
          "New Stochastic\nState Vector  $\\mathbf{x}^{(r+1)}$",
          fontsize=14.5, fontweight="bold")
arrow(ax, (MTJ_X + 1.50, BLOCK_Y), (MTJ_X + 1.50, NSV_Y + NSV_H), lw=1.6)


# ===== Feedback path: x^(r+1) -> x^(r), under Expectation Estimation =====
fb_verts = [
    (NSV_X, NSV_Y + NSV_H / 2),
    (NSV_X, 0.20),
    (0.85, 0.20),
    (0.85, INPUT_Y + 0.02),
]
fb_codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO]
ax.add_patch(PathPatch(MplPath(fb_verts, fb_codes),
                       edgecolor=INK, linewidth=1.9,
                       facecolor="none", zorder=2))
ax.annotate("", xy=(0.85, INPUT_Y + 0.04), xytext=(0.85, INPUT_Y - 0.25),
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.9), zorder=3)


# ===== Expectation Estimation -> Approximated E[s] =====
EXP_X, EXP_Y, EXP_W, EXP_H = 5.50, 0.50, 5.50, 1.30
small_box(ax, EXP_X, EXP_Y, EXP_W, EXP_H,
          "Expectation Estimation\n(Spatial/Temporal Averaging)",
          fontsize=14.5, fontweight="bold")
arrow(ax, (EXP_X + EXP_W, EXP_Y + EXP_H / 2),
      (EXP_X + EXP_W + 0.80, EXP_Y + EXP_H / 2), lw=1.9)
ax.text(EXP_X + EXP_W + 0.92, EXP_Y + EXP_H / 2,
        r"Approximated  $\mathbb{E}[s]$",
        fontsize=15.5, color=INK, ha="left", va="center", fontweight="bold")


# ===== Save =====
out_dir = Path(__file__).resolve().parents[1] / "article" / "figs"
png_path = out_dir / "Chapter04_local_01.png"
pdf_path = out_dir / "Chapter04_local_01.pdf"
fig.savefig(png_path, dpi=320, bbox_inches="tight", facecolor="white")
fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
print(f"saved {png_path.name}")
print(f"saved {pdf_path.name}")
