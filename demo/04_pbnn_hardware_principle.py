"""
Fig 4.1 -- sMTJ-PBNN hardware principle (top-journal layout, Arial).

Three coupled functional blocks plus a feedback loop on the same physical
sMTJ substrate:

  1. MRAM CIM weight array runs a deterministic XNOR-popcount column sum
     over the stochastic input vector x^(r).
  2. The sky130-grounded periphery digitizes the column current with the
     slope-matched read-out (transimpedance + StrongARM, or a column-shared
     SAR), maps it to p = g(a), and drives the write line via the resistor-
     string write-DAC with IR-aware pre-distortion and a CMOS driver.
  3. Stochastic MTJ sampling array converts u into a new state vector
     x^(r+1) via thermal-activation switching.

x^(r+1) feeds back as the next input; spatial / temporal averaging across
cycles delivers the approximated expectation E[s].

Output: demo/figures/04_pbnn_hardware_principle.png (raw, unnumbered;
the chapter deck adds the figure number — see eda/build_ppt_figs.py).
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (
    Ellipse, FancyArrowPatch, FancyBboxPatch, PathPatch, Polygon, Rectangle,
)
from matplotlib.path import Path as MplPath


INK         = "#2E1F4D"
PURPLE      = "#563A86"
PURPLE_MID  = "#8467B1"
PURPLE_FILL = "#E9E2F3"
PURPLE_FAINT= "#F7F4FB"
PURPLE_FREE = "#9B7DBE"   # free layer  (lighter)
PURPLE_PIN  = "#5E437F"   # pinned layer (darker)
PURPLE_DARK = "#3F2A66"   # bottom-cap shadow
BARRIER     = "#F2EAFA"   # tunnel barrier (very light)
GRAY        = "#55515B"


mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "mathtext.fontset": "dejavusans",
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


def arrow(ax, start, end, label=None, label_offset=(0.0, 0.32),
          label_size=15, lw=1.9):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="-|>", mutation_scale=22,
        linewidth=lw, color=INK,
        shrinkA=2, shrinkB=2, zorder=3,
    ))
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha="center", va="center",
                fontsize=label_size, color=INK, style="italic", zorder=4)


def draw_mtj(ax, cx, cy, w=0.55, h=0.86):
    """
    sMTJ stack: top electrode cap -> free layer -> tunnel barrier ->
    pinned layer -> bottom electrode (darker shadow). The barrier band
    in the middle is the visual marker that distinguishes this from a
    plain cylinder.
    """
    ell_h    = 0.16
    barrier_h = 0.10
    body_top  = cy + h / 2 - ell_h / 2     # where the top ellipse sits
    body_bot  = cy - h / 2 + ell_h / 2     # where the bottom ellipse sits
    # split body into upper (free) and lower (pinned) around the barrier
    barrier_y = cy - barrier_h / 2 - 0.01
    free_y    = barrier_y + barrier_h
    free_h    = body_top - free_y
    pinned_h  = barrier_y - body_bot

    # Pinned layer (lower, darker)
    ax.add_patch(Rectangle(
        (cx - w / 2, body_bot), w, pinned_h,
        facecolor=PURPLE_PIN, edgecolor=PURPLE, linewidth=1.0, zorder=5,
    ))
    # Tunnel barrier (thin light band)
    ax.add_patch(Rectangle(
        (cx - w / 2, barrier_y), w, barrier_h,
        facecolor=BARRIER, edgecolor=PURPLE, linewidth=0.8, zorder=6,
    ))
    # Free layer (upper, lighter)
    ax.add_patch(Rectangle(
        (cx - w / 2, free_y), w, free_h,
        facecolor=PURPLE_FREE, edgecolor=PURPLE, linewidth=1.0, zorder=5,
    ))
    # Top cap (electrode face)
    ax.add_patch(Ellipse(
        (cx, body_top), w, ell_h,
        facecolor=PURPLE_FILL, edgecolor=PURPLE, linewidth=1.0, zorder=7,
    ))
    # Bottom cap (electrode shadow)
    ax.add_patch(Ellipse(
        (cx, body_bot), w, ell_h,
        facecolor=PURPLE_DARK, edgecolor=PURPLE, linewidth=1.0, zorder=4,
    ))


def draw_pulse(ax, cx, cy, w=0.66, h=0.58):
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


def draw_squiggle(ax, x0, y0, dx=0.74, amp=0.10, cycles=3):
    xs = np.linspace(x0, x0 + dx, 90)
    ys = y0 + amp * np.sin((xs - x0) / dx * cycles * 2 * np.pi)
    ax.plot(xs, ys, color=INK, linewidth=1.5, zorder=4)


# ----------------------------------------------------------------------------
# Figure
# ----------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(16.7, 9.5))
ax.set_xlim(0, 17)
ax.set_ylim(0, 9.4)
ax.axis("off")
ax.set_aspect("equal", adjustable="box")


# Shared top-row geometry
BLOCK_Y, BLOCK_TOP = 2.70, 9.10
BLOCK_H = BLOCK_TOP - BLOCK_Y


# ===== Stochastic Input Vector =====
INPUT_X, INPUT_Y, INPUT_W, INPUT_H = 0.35, 4.05, 1.55, 4.15
small_box(ax, INPUT_X, INPUT_Y, INPUT_W, INPUT_H,
          "Stochastic\nInput\nVector\n\n$\\mathbf{x}^{(r)}$",
          fontsize=14.5, fontweight="bold")
arrow(ax, (INPUT_X + INPUT_W, 6.18), (2.35, 6.18), lw=2.0)


# ===== MRAM CIM Weight Array =====
MRAM_X, MRAM_W = 2.35, 5.00
rounded_block(ax, MRAM_X, BLOCK_Y, MRAM_W, BLOCK_H)
TITLE_SIZE = 15.2
SUBTITLE_SIZE = 11.8

ax.text(MRAM_X + MRAM_W / 2, 8.78, "MRAM CIM Weight Array",
        ha="center", va="top", fontsize=TITLE_SIZE, color=INK,
        fontweight="bold", zorder=3)
ax.text(MRAM_X + MRAM_W / 2, 8.40, "(Deterministic Computation)",
        ha="center", va="top", fontsize=SUBTITLE_SIZE, color=INK,
        style="italic", zorder=3)

# Crossbar
COLS, ROWS = 4, 4
xb_col_xs = np.array([
    MRAM_X + 1.07,
    MRAM_X + 1.72,
    MRAM_X + 2.37,
    MRAM_X + 3.62,
])
xb_row_ys = np.array([6.92, 6.18, 5.44, 4.56])
MTJ_W_XB, MTJ_H_XB = 0.46, 0.60
WL_STUB_X = MRAM_X + 0.18
WL_STUB_W, WL_STUB_H = 0.22, 0.30
WL_WEDGE_X = WL_STUB_X + WL_STUB_W
WL_WEDGE_TIP_X = WL_WEDGE_X + 0.18
WL_LINE_X0 = WL_WEDGE_TIP_X
WL_LINE_X1 = xb_col_xs[-1] + 0.58
WL_LABEL_X = xb_col_xs[0] - 0.34

# WL rows
for i, ry in enumerate(xb_row_ys):
    ax.add_patch(Rectangle(
        (WL_STUB_X, ry - WL_STUB_H / 2), WL_STUB_W, WL_STUB_H,
        facecolor=PURPLE_MID, edgecolor=PURPLE, linewidth=1.1, zorder=6,
    ))
    ax.add_patch(Polygon(
        [[WL_WEDGE_X, ry - WL_STUB_H / 2],
         [WL_WEDGE_TIP_X, ry],
         [WL_WEDGE_X, ry + WL_STUB_H / 2]],
        closed=True, facecolor=PURPLE, edgecolor=PURPLE, linewidth=1.0, zorder=6,
    ))
    ax.plot([WL_LINE_X0, WL_LINE_X1], [ry, ry],
            color=GRAY, linewidth=1.1, zorder=3)
    idx = f"{i}" if i < ROWS - 1 else "i"
    ax.text(WL_LABEL_X, ry + 0.14, f"WL$_{{{idx}}}$",
            fontsize=10.2, color=INK, ha="right", va="bottom", zorder=7)

# BL / RL labels & vertical column lines
for j, cx in enumerate(xb_col_xs):
    ax.plot([cx, cx], [xb_row_ys[-1] - 0.30, xb_row_ys[0] + 0.38],
            color=GRAY, linewidth=1.1, zorder=3)
    jdx = f"{j}" if j < COLS - 1 else "j"
    ax.text(cx, 7.62, f"BL$_{{{jdx}}}$",
            fontsize=11.2, color=INK, ha="center", va="bottom", zorder=4)
    ax.text(cx + 0.07, 7.35, f"$RL_{{{jdx}}}$",
            fontsize=9.2, color=GRAY, style="italic",
            ha="left", va="bottom", zorder=4)

ax.text((xb_col_xs[2] + xb_col_xs[3]) / 2, 7.68, r"$\cdots$",
        fontsize=12.6, color=INK, ha="center", va="center", zorder=4)

# MTJs + W_ij labels
for i, ry in enumerate(xb_row_ys):
    for j, cx in enumerate(xb_col_xs):
        draw_mtj(ax, cx, ry, w=MTJ_W_XB, h=MTJ_H_XB)
        idx = f"{i}" if i < ROWS - 1 else "i"
        jdx = f"{j}" if j < COLS - 1 else "j"
        # White weight labels sit on the dark pinned layer for contrast.
        ax.text(cx, ry - 0.14, f"$W_{{{idx}{jdx}}}$",
                fontsize=7.6, color="white", ha="center", va="center",
                fontweight="bold", zorder=8)

# Inter-column ellipsis between j=2 and j=j
ell_col_x = (xb_col_xs[-2] + xb_col_xs[-1]) / 2
for ry in xb_row_ys:
    ax.text(ell_col_x, ry, r"$\cdots$",
            fontsize=11.8, color=INK, ha="center", va="center", zorder=4)

# Inter-row ellipsis between i=2 and i=i
ell_row_y = (xb_row_ys[-2] + xb_row_ys[-1]) / 2
ax.text(MRAM_X + 0.42, ell_row_y, r"$\vdots$",
        fontsize=12.8, color=INK, ha="center", va="center", zorder=4)
for cx in xb_col_xs:
    ax.text(cx, ell_row_y, r"$\vdots$",
            fontsize=11.2, color=INK, ha="center", va="center", zorder=4)

# Bottom column-current arrows
ARROW_TOP_Y, ARROW_BOT_Y = 4.18, 3.78
for cx in xb_col_xs:
    ax.annotate("", xy=(cx, ARROW_BOT_Y), xytext=(cx, ARROW_TOP_Y),
                arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.3),
                zorder=3)

# Bottom legends
brace_l, brace_r, brace_y = xb_col_xs[0] - 0.24, xb_col_xs[-1] + 0.24, 3.54
ax.plot([brace_l, brace_l, brace_r, brace_r],
        [brace_y + 0.12, brace_y, brace_y, brace_y + 0.12],
        color=INK, linewidth=1.1, zorder=4)
ax.text((brace_l + brace_r) / 2, 3.36,
        r"analog column-current vector  $\mathbf{I}_{\mathrm{col}}$",
        fontsize=9.1, color=INK, style="italic",
        ha="center", va="center", zorder=4)

ax.text(MRAM_X + 1.58, 2.95,
        r"$I_{\mathrm{col}}\propto\sum \mathrm{XNOR}(x,w)$",
        fontsize=9.1, color=INK, style="italic",
        ha="center", va="center", zorder=4)
ax.text(MRAM_X + 3.80, 2.95, "KCL summation",
        fontsize=9.1, color=INK, style="italic",
        ha="center", va="center", zorder=4)


# I_col arrow (MRAM -> Map)
arrow(ax, (MRAM_X + MRAM_W, 6.10), (7.90, 6.10),
      label="$I_{\\mathrm{col}}$", label_offset=(0, 0.32), label_size=16)


# ===== Probability Mapping & Stochastic Write Driver =====
MAP_X, MAP_W = 7.90, 3.05
rounded_block(ax, MAP_X, BLOCK_Y, MAP_W, BLOCK_H)
ax.text(MAP_X + MAP_W / 2, 8.76,
        "Probability Mapper\nWrite Driver",
        ha="center", va="top", fontsize=TITLE_SIZE, color=INK,
        fontweight="bold", linespacing=1.05, zorder=3)

# read-out + map sub-box (slope-matched read-out digitizes I_col -> a -> p)
small_box(ax, MAP_X + 0.24, 6.10, MAP_W - 0.48, 1.35,
          "slope-matched read-out\n(TIA + StrongARM / SAR)\n$a \\to p=g(a)$", fontsize=10.6)
# Down-arrow
arrow(ax, (MAP_X + MAP_W / 2, 6.08), (MAP_X + MAP_W / 2, 5.05), lw=1.6)
# write-driver sub-box (resistor-string write-DAC + IR pre-distortion + CMOS driver)
small_box(ax, MAP_X + 0.24, 3.55, MAP_W - 0.48, 1.35,
          "write driver\nR-string DAC + IR\npre-distortion + CMOS", fontsize=10.6)
# sky130-grounding note for the periphery block
ax.text(MAP_X + MAP_W / 2, 3.18, "sky130-extracted periphery",
        fontsize=8.6, color=PURPLE, style="italic", ha="center", va="center", zorder=4)


# u arrow (Map -> MTJ Sampling)
arrow(ax, (MAP_X + MAP_W, 4.22), (MAP_X + MAP_W + 0.55, 4.22),
      label="$u$", label_offset=(0, 0.32), label_size=16)


# ===== Stochastic MTJ Sampling Array =====
MTJ_X, MTJ_W = MAP_X + MAP_W + 0.55, 4.95
rounded_block(ax, MTJ_X, BLOCK_Y, MTJ_W, BLOCK_H)
ax.text(MTJ_X + MTJ_W / 2, 8.78, "Stochastic MTJ",
        ha="center", va="top", fontsize=TITLE_SIZE, color=INK,
        fontweight="bold", zorder=3)
ax.text(MTJ_X + MTJ_W / 2, 8.42, "Sampling Array",
        ha="center", va="top", fontsize=TITLE_SIZE, color=INK,
        fontweight="bold", zorder=3)
ax.text(MTJ_X + MTJ_W / 2, 8.03, "(Thermal Switching)",
        ha="center", va="top", fontsize=SUBTITLE_SIZE, color=INK,
        style="italic", zorder=3)

# Write pulses caption
ax.text(MTJ_X + 0.25, 7.30, "Write pulses",
        fontsize=12.4, color=INK, ha="left", va="center", zorder=4)
ax.text(MTJ_X + MTJ_W - 0.24, 5.50,
        "Thermal\nnoise\nflip",
        fontsize=9.4, color=INK, ha="right", va="center",
        linespacing=1.05, zorder=4)

sample_ys = [6.64, 5.55, 4.46]
pulse_x = MTJ_X + 0.55
cell_x = MTJ_X + 1.55
bus_x = MTJ_X + 3.12
wave_x = MTJ_X + 3.36

ax.plot([bus_x, bus_x], [sample_ys[-1] - 0.46, sample_ys[0] + 0.46],
        color=INK, linewidth=1.6, zorder=3)
for k, cy in enumerate(sample_ys):
    draw_pulse(ax, pulse_x, cy + 0.02, w=0.62, h=0.52)
    draw_mtj(ax, cell_x, cy, w=0.70, h=0.98)
    ax.text(cell_x + 0.53, cy, "MTJ",
            fontsize=11.6, color=INK, ha="left", va="center", zorder=5)
    ax.plot([cell_x + 1.02, bus_x], [cy, cy],
            color=INK, linewidth=1.4, zorder=3)
    ax.add_patch(Ellipse((bus_x, cy), 0.10, 0.10,
                         facecolor=INK, edgecolor=INK, zorder=5))
    draw_squiggle(ax, wave_x, cy + 0.14, dx=0.50, amp=0.075, cycles=2.5)
    draw_squiggle(ax, wave_x, cy - 0.10, dx=0.50, amp=0.075, cycles=2.5)

ax.text(pulse_x, (sample_ys[0] + sample_ys[1]) / 2, r"$\vdots$",
        fontsize=18, color=INK, ha="center", va="center", zorder=4)
ax.text(cell_x, (sample_ys[1] + sample_ys[2]) / 2, r"$\vdots$",
        fontsize=18, color=INK, ha="center", va="center", zorder=4)


# ===== New Stochastic State Vector =====
NSV_X, NSV_Y, NSV_W, NSV_H = MTJ_X + 0.48, 2.88, MTJ_W - 0.96, 0.82
small_box(ax, NSV_X, NSV_Y, NSV_W, NSV_H,
          "New Stochastic\nState Vector  $\\mathbf{x}^{(r+1)}$",
          fontsize=12.5, fontweight="bold")
arrow(ax, (bus_x, sample_ys[-1] - 0.50), (bus_x, NSV_Y + NSV_H), lw=1.6)


# ===== Expectation Estimation -> Approximated E[s] =====
EXP_X, EXP_Y, EXP_W, EXP_H = 5.95, 0.82, 5.35, 1.08
small_box(ax, EXP_X, EXP_Y, EXP_W, EXP_H,
          "Expectation Estimation\n(Spatial/Temporal Averaging)",
          fontsize=13.4, fontweight="bold")
arrow(ax, (EXP_X + EXP_W, EXP_Y + EXP_H / 2),
      (EXP_X + EXP_W + 0.78, EXP_Y + EXP_H / 2), lw=1.9)
ax.text(EXP_X + EXP_W + 0.90, EXP_Y + EXP_H / 2,
        r"Approximated  $\mathbb{E}[s]$",
        fontsize=14.6, color=INK, ha="left", va="center", fontweight="bold")


# ===== Feedback loop: x^(r+1) -> x^(r), routed in the mid-lower lane =====
fb_y = 2.35
fb_verts = [
    (NSV_X + NSV_W / 2, NSV_Y),
    (NSV_X + NSV_W / 2, fb_y),
    (0.98, fb_y),
    (0.98, INPUT_Y + 0.02),
]
fb_codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO]
ax.add_patch(PathPatch(MplPath(fb_verts, fb_codes),
                       edgecolor=INK, linewidth=1.9,
                       facecolor="none", zorder=2,
                       capstyle="round", joinstyle="round"))
# Arrowhead entering Input Vector from below
ax.annotate("", xy=(0.98, INPUT_Y + 0.04), xytext=(0.98, INPUT_Y - 0.30),
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=2.2), zorder=3)

# ===== Save =====
out_dir = Path(__file__).resolve().parent / "figures"
png_path = out_dir / "04_pbnn_hardware_principle.png"
pdf_path = out_dir / "04_pbnn_hardware_principle.pdf"
fig.savefig(png_path, dpi=320, bbox_inches="tight", facecolor="white")
fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
print(f"saved {png_path.name}")
print(f"saved {pdf_path.name}")
