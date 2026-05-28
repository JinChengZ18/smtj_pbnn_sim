"""
Fig 4.1 -- sMTJ-PBNN hardware principle.

Three coupled functional blocks plus a feedback loop on the same physical
sMTJ substrate:

  1. MRAM CIM weight array runs a deterministic XNOR-popcount column sum
     over the stochastic input vector x^(r).
  2. Probability mapping & stochastic write driver convert the column
     current into a write stimulus u for the device array.
  3. Stochastic MTJ sampling array converts u into a new state vector
     x^(r+1) via thermal-activation switching.

The new state x^(r+1) feeds back as the next input, and spatial/temporal
averaging across many cycles delivers the approximated expectation E[s]
read at inference time.

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
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "mathtext.fontset": "dejavusans",
    "axes.unicode_minus": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def block(ax, x, y, w, h, title, subtitle=None,
          fill=PURPLE_FAINT, edge=PURPLE,
          title_size=12.5, subtitle_size=10.0,
          title_lines_gap=0.42):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.03,rounding_size=0.10",
        linewidth=1.5, edgecolor=edge, facecolor=fill, zorder=1,
    ))
    title_lines = title.count("\n") + 1
    title_top = y + h - 0.30
    ax.text(x + w / 2, title_top, title,
            ha="center", va="top",
            fontsize=title_size, color=INK, fontweight="bold",
            linespacing=1.0, zorder=3)
    if subtitle is not None:
        ax.text(x + w / 2,
                title_top - title_lines * title_lines_gap,
                f"({subtitle})",
                ha="center", va="top",
                fontsize=subtitle_size, color=INK, style="italic", zorder=3)


def small_box(ax, x, y, w, h, text,
              fill=PURPLE_FILL, edge=PURPLE,
              fontsize=10.0, fontweight="normal"):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.025,rounding_size=0.08",
        linewidth=1.2, edgecolor=edge, facecolor=fill, zorder=2,
    ))
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center",
            fontsize=fontsize, color=INK,
            fontweight=fontweight, linespacing=1.15, zorder=3)


def arrow(ax, start, end, label=None, label_offset=(0.0, 0.20),
          label_size=11.0, rad=0.0, lw=1.5, dashed=False):
    arr = FancyArrowPatch(
        start, end,
        arrowstyle="-|>", mutation_scale=15,
        linewidth=lw, color=INK,
        linestyle=(0, (5, 3)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=2, shrinkB=2, zorder=2,
    )
    ax.add_patch(arr)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(mx, my, label,
                ha="center", va="center",
                fontsize=label_size, color=INK, style="italic", zorder=4)


def draw_mtj(ax, cx, cy, w=0.34, h=0.46, color=PURPLE_MTJ):
    ax.add_patch(Rectangle(
        (cx - w / 2, cy - h / 2 + 0.07), w, h - 0.14,
        facecolor=color, edgecolor=PURPLE, linewidth=0.9, zorder=5,
    ))
    ax.add_patch(Ellipse(
        (cx, cy + h / 2 - 0.07), w, 0.14,
        facecolor=PURPLE_FILL, edgecolor=PURPLE, linewidth=0.9, zorder=6,
    ))
    ax.add_patch(Ellipse(
        (cx, cy - h / 2 + 0.07), w, 0.14,
        facecolor=color, edgecolor=PURPLE, linewidth=0.9, zorder=5,
    ))


def draw_write_pulse(ax, cx, cy, w=0.55, h=0.42):
    pts = [
        (cx - w / 2,         cy - h / 3),
        (cx - w / 4 - 0.02,  cy - h / 3),
        (cx - w / 4 - 0.02,  cy + h / 3),
        (cx + w / 4 + 0.02,  cy + h / 3),
        (cx + w / 4 + 0.02,  cy - h / 3),
        (cx + w / 2,         cy - h / 3),
    ]
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=INK, linewidth=1.3, zorder=4)


def draw_squiggle(ax, x0, y0, dx=0.55, amp=0.07, cycles=2.5):
    xs = np.linspace(x0, x0 + dx, 80)
    ys = y0 + amp * np.sin((xs - x0) / dx * cycles * 2 * np.pi)
    ax.plot(xs, ys, color=INK, linewidth=1.1, zorder=4)


def draw_crossbar(ax, x0, y0, w, h, rows=4, cols=4):
    row_ys = np.linspace(y0 + h - 0.60, y0 + 1.10, rows)
    col_xs = np.linspace(x0 + 1.00, x0 + w - 0.45, cols)

    for i, ry in enumerate(row_ys):
        ax.add_patch(Rectangle(
            (x0 - 0.05, ry - 0.13), 0.22, 0.26,
            facecolor=PURPLE_MID, edgecolor=PURPLE, linewidth=0.9, zorder=6,
        ))
        ax.plot([x0 + 0.17, col_xs[-1] + 0.30], [ry, ry],
                color=GRAY, linewidth=0.7, zorder=3)
        idx = f"{i}" if i < rows - 1 else "i"
        ax.text(x0 + 0.35, ry + 0.21, f"WL$_{{{idx}}}$",
                fontsize=9.2, color=INK, ha="left", va="bottom", zorder=4)

    top_y = row_ys[0] + 0.42
    bot_y = row_ys[-1] - 0.40
    for j, cx in enumerate(col_xs):
        ax.plot([cx, cx], [bot_y, top_y],
                color=GRAY, linewidth=0.7, zorder=3)
        jdx = f"{j}" if j < cols - 1 else "j"
        ax.text(cx, top_y + 0.55, f"BL$_{{{jdx}}}$",
                fontsize=9.2, color=INK, ha="center", va="bottom", zorder=4)
        ax.text(cx + 0.10, top_y + 0.20, f"$RL_{{{jdx}}}$",
                fontsize=8.6, color=GRAY, style="italic",
                ha="left", va="bottom", zorder=4)

    for i, ry in enumerate(row_ys):
        for j, cx in enumerate(col_xs):
            draw_mtj(ax, cx, ry)
            idx = f"{i}" if i < rows - 1 else "i"
            jdx = f"{j}" if j < cols - 1 else "j"
            ax.text(cx, ry, f"$W_{{{idx}{jdx}}}$",
                    fontsize=7.2, color="white", ha="center", va="center",
                    fontweight="bold", zorder=8)

    for j, cx in enumerate(col_xs):
        ax.annotate("",
                    xy=(cx, y0 + 0.45),
                    xytext=(cx, bot_y),
                    arrowprops=dict(arrowstyle="-|>", color=GRAY, lw=1.0),
                    zorder=3)
    ax.text(x0 + 0.10, y0 + 0.62, "Analog Currents",
            fontsize=9.0, color=GRAY, style="italic",
            ha="left", va="center", zorder=4)
    for j in range(min(3, cols)):
        ax.text(col_xs[j] + 0.13, y0 + 0.45,
                f"$I_{{\\mathrm{{col}},{j}}}$",
                fontsize=8.4, color=INK, ha="left", va="center", zorder=4)

    ax.text(x0 + w / 2, y0 + 0.10,
            r"$I_{\mathrm{col}}\propto\sum\mathrm{XNOR}(x,w)$"
            "         KCL Summation",
            fontsize=9.4, color=INK, style="italic",
            ha="center", va="center", zorder=4)


fig, ax = plt.subplots(figsize=(14.2, 9.0))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis("off")
ax.set_aspect("equal", adjustable="box")

small_box(ax, 0.30, 4.50, 1.55, 3.90,
          "Stochastic\nInput\nVector\n\n$\\mathbf{x}^{(r)}$",
          fontsize=11.5)

arrow(ax, (1.85, 6.45), (2.40, 6.45), lw=1.6)

block(ax, 2.40, 2.30, 5.85, 7.20,
      "MRAM CIM Weight Array",
      subtitle="Deterministic Computation",
      title_size=13, subtitle_size=10.5)
draw_crossbar(ax, 2.75, 2.30, 5.20, 5.55, rows=4, cols=4)

arrow(ax, (8.25, 6.20), (8.85, 6.20),
      label="$I_{\\mathrm{col}}$", label_offset=(0.0, 0.25))

block(ax, 8.85, 3.40, 2.65, 6.10,
      "Probability Mapping\n&\nStochastic Write Driver",
      title_size=12, title_lines_gap=0.55)
small_box(ax, 9.05, 6.80, 2.25, 1.25,
          "$p = g(a)$\n(Nonlinear Mapping)", fontsize=10.5)
arrow(ax, (10.175, 6.78), (10.175, 5.65), lw=1.3)
small_box(ax, 9.05, 4.40, 2.25, 1.25,
          "$(u)$ Generator\nWrite Stimulus", fontsize=10.5)

arrow(ax, (11.50, 5.00), (12.05, 5.00),
      label="$u$", label_offset=(0.0, 0.25))

block(ax, 12.05, 3.40, 3.85, 6.10,
      "Stochastic MTJ\nSampling Array",
      subtitle="Thermal Switching",
      title_size=12.5, subtitle_size=10.0, title_lines_gap=0.42)

ax.text(12.30, 7.85, "Write pulses",
        fontsize=10.0, color=INK, ha="left", va="center", zorder=4)

mtj_top = 7.30
mtj_bot = 4.85
draw_write_pulse(ax, 12.45, mtj_top + 0.05, w=0.55, h=0.45)
draw_mtj(ax, 13.30, mtj_top, w=0.50, h=0.62)
ax.text(13.62, mtj_top + 0.04, "MTJ", fontsize=9.5, color=INK,
        ha="left", va="center", zorder=5)
draw_squiggle(ax, 14.20, mtj_top + 0.15, dx=0.55, amp=0.07, cycles=3)
draw_squiggle(ax, 14.20, mtj_top - 0.05, dx=0.55, amp=0.07, cycles=3)

draw_write_pulse(ax, 12.45, mtj_bot + 0.05, w=0.55, h=0.45)
draw_mtj(ax, 13.30, mtj_bot, w=0.50, h=0.62)
ax.text(13.62, mtj_bot + 0.04, "MTJ", fontsize=9.5, color=INK,
        ha="left", va="center", zorder=5)
draw_squiggle(ax, 14.20, mtj_bot + 0.15, dx=0.55, amp=0.07, cycles=3)
draw_squiggle(ax, 14.20, mtj_bot - 0.05, dx=0.55, amp=0.07, cycles=3)

ax.text(12.45, (mtj_top + mtj_bot) / 2, r"$\vdots$",
        fontsize=15, color=INK, ha="center", va="center", zorder=4)
ax.text(13.30, (mtj_top + mtj_bot) / 2, r"$\vdots$",
        fontsize=15, color=INK, ha="center", va="center", zorder=4)

ax.text(14.95, (mtj_top + mtj_bot) / 2,
        "Thermal\nFluctuations\n&\nProbabilistic\nFlip",
        fontsize=9.5, color=INK, ha="center", va="center",
        linespacing=1.15, zorder=4)

small_box(ax, 11.85, 2.20, 4.05, 0.90,
          "New Stochastic State Vector  $\\mathbf{x}^{(r+1)}$",
          fontsize=10.5, fontweight="bold")
arrow(ax, (13.90, 3.38), (13.90, 3.12), lw=1.3)

fb_verts = [
    (12.30, 2.20),
    (12.30, 0.12),
    (1.05, 0.12),
    (1.05, 4.48),
]
fb_codes = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO, MplPath.LINETO]
ax.add_patch(PathPatch(MplPath(fb_verts, fb_codes),
                       edgecolor=INK, linewidth=1.6,
                       facecolor="none", zorder=2))
ax.annotate("", xy=(1.05, 4.50), xytext=(1.05, 4.25),
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.6), zorder=3)
ax.text(1.35, 3.20, "feedback",
        fontsize=9.5, color=GRAY, style="italic",
        ha="left", va="center", zorder=3)

small_box(ax, 5.90, 0.30, 4.80, 1.10,
          "Expectation Estimation\n(Spatial/Temporal Averaging)",
          fontsize=10.5)
arrow(ax, (10.70, 0.85), (11.65, 0.85))
ax.text(11.78, 0.85,
        r"Approximated  $\mathbb{E}[s]$",
        fontsize=11.5, color=INK, ha="left", va="center")

ax.plot([8.30, 8.30], [2.20, 1.40],
        color=INK, linewidth=1.0, linestyle=(0, (4, 2)),
        alpha=0.75, zorder=2)
ax.annotate("", xy=(8.30, 1.40), xytext=(8.30, 1.55),
            arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.0), zorder=3)

out_dir = Path(__file__).resolve().parents[1] / "article" / "figs"
png_path = out_dir / "Chapter04_local_01.png"
pdf_path = out_dir / "Chapter04_local_01.pdf"
fig.savefig(png_path, dpi=320, bbox_inches="tight", facecolor="white")
fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
print(f"saved {png_path.name}")
print(f"saved {pdf_path.name}")
