"""
fig_space_time  v2 — full redesign:
  2×2 equal-width grid (no 品字形):
    [0,0]  Pipeline stages 1–2: distribution params + sMTJ sampling
    [0,1]  Pipeline stages 3–4: in-array XNOR-popcount + temporal aggregation
    [1,0]  Spatial tiling (conventional CIM)
    [1,1]  Temporal unfolding (this work)
  Fixes:
    – removed (a)(b)(c) numbering
    – all text fits inside boxes; no annotation arrows crossing boxes
    – inter-panel arrow drawn with ConnectionPatch
    – larger bitstream cells; bigger aggregation box
    – no set_aspect('equal') on any panel (coordinate units ≈ square naturally)
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import matplotlib as mpl
import numpy as np

PURPLE_DEEP  = "#6E2E83"
PURPLE_MID   = "#9B6AB5"
PURPLE_LIGHT = "#C8A8DA"
PURPLE_FAINT = "#ECDFF2"
GRAY_EDGE    = "#555555"
ACCENT       = "#8B3A62"

mpl.rcParams.update({
    "font.family":    "serif",
    "font.serif":     ["Arial", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset": "stix",
})

fig = plt.figure(figsize=(13.5, 8.6))
gs = fig.add_gridspec(2, 2,
                       height_ratios=[1.0, 1.25],
                       width_ratios=[1.0, 1.0],
                       hspace=0.20, wspace=0.14)

ax00 = fig.add_subplot(gs[0, 0])
ax01 = fig.add_subplot(gs[0, 1])
ax10 = fig.add_subplot(gs[1, 0])
ax11 = fig.add_subplot(gs[1, 1])

# Shared FancyBboxPatch helper
def rbox(ax, xy, w, h, fc, ec=PURPLE_DEEP, lw=1.15):
    p = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.07",
                       facecolor=fc, edgecolor=ec, linewidth=lw, clip_on=False)
    ax.add_patch(p)
    return p

# ─────────────────────────────────────────────────────────────────────────────
#  Top-left [0,0]:  Stages 1 & 2 — Parameters  →  Stochastic sampling
# ─────────────────────────────────────────────────────────────────────────────
ax = ax00
ax.set_xlim(0, 10);  ax.set_ylim(0, 7)
ax.axis("off")
ax.set_title("Weight parameterization  →  Stochastic sampling",
             fontsize=10.5, pad=8)

# Category labels above divider line
ax.plot([0.15, 9.85], [6.70, 6.70], color=GRAY_EDGE, lw=0.55, alpha=0.5)
ax.text(2.20, 6.85, "Storage / DAC", fontsize=7.8, color=GRAY_EDGE, ha="center")
ax.text(7.45, 6.85, "Entropy source (sMTJ)", fontsize=7.8, color=GRAY_EDGE, ha="center")

# ── Block 1: distribution parameters ──────────────────────────────────────
rbox(ax, (0.15, 0.35), 4.05, 6.08, PURPLE_FAINT)

ax.text(2.22, 5.95, "Distribution\nparameters",
        ha="center", va="center", fontsize=10, color=PURPLE_DEEP, fontweight="bold")
ax.text(2.22, 4.62, r"$\theta_{ij} \;\Rightarrow\; p_{ij} = \sigma(\theta_{ij})$",
        ha="center", va="center", fontsize=10.5, color="black")
ax.text(2.22, 3.42, "Stored in SRAM register;\nconverted to $V_{\\rm wr}$ by DAC\nevery sampling cycle",
        ha="center", va="center", fontsize=8.2, color=GRAY_EDGE, style="italic",
        linespacing=1.45)
ax.text(2.22, 1.68, r"$\theta_{ij} \in \mathbb{R}$  (trainable scalar)",
        ha="center", va="center", fontsize=8.5, color=GRAY_EDGE)
ax.text(2.22, 0.88, r"$p_{ij} = \sigma(\theta_{ij}) \in (0,1)$",
        ha="center", va="center", fontsize=8.5, color=GRAY_EDGE)

# ── Arrow block 1 → block 2 ────────────────────────────────────────────────
ax.annotate("", xy=(5.18, 3.42), xytext=(4.28, 3.42),
            arrowprops=dict(arrowstyle="-|>", color=GRAY_EDGE, lw=1.5,
                            mutation_scale=14))

# ── Block 2: stochastic sampling ──────────────────────────────────────────
rbox(ax, (5.28, 0.35), 4.55, 6.08, "#F8F0D9", ec=ACCENT, lw=1.3)

ax.text(7.55, 5.95, "Stochastic\nsampling",
        ha="center", va="center", fontsize=10, color=ACCENT, fontweight="bold")
ax.text(7.55, 4.65, r"$w_{ij}^{(t)} \sim \mathrm{Bern}(p_{ij})$",
        ha="center", va="center", fontsize=10.5, color="black")
ax.text(7.55, 3.50, "sMTJ thermal switching\n(write pulse $V_{\\rm wr} = V_0 + V_T\\theta_{ij}$)",
        ha="center", va="center", fontsize=8.2, color=GRAY_EDGE, style="italic",
        linespacing=1.45)
ax.text(7.55, 1.95, r"$P_\mathrm{sw}(V) \approx \sigma\!\left(\dfrac{V - V_0}{V_T}\right)$",
        ha="center", va="center", fontsize=9.0, color=GRAY_EDGE)
ax.text(7.55, 0.88, r"switching rate $\sim$ ns",
        ha="center", va="center", fontsize=8.0, color=GRAY_EDGE, style="italic")

# ─────────────────────────────────────────────────────────────────────────────
#  Top-right [0,1]:  Stages 3 & 4 — XNOR-popcount  →  Temporal aggregation
# ─────────────────────────────────────────────────────────────────────────────
ax = ax01
ax.set_xlim(0, 10);  ax.set_ylim(0, 7)
ax.axis("off")
ax.set_title("In-array XNOR-popcount  →  Temporal aggregation",
             fontsize=10.5, pad=8)

ax.plot([0.15, 9.85], [6.70, 6.70], color=GRAY_EDGE, lw=0.55, alpha=0.5)
ax.text(2.22, 6.85, "In-memory arithmetic", fontsize=7.8, color=GRAY_EDGE, ha="center")
ax.text(7.45, 6.85, "Statistical read-out", fontsize=7.8, color=GRAY_EDGE, ha="center")

# ── Block 3: XNOR-popcount ────────────────────────────────────────────────
rbox(ax, (0.15, 0.35), 4.05, 6.08, PURPLE_FAINT)

ax.text(2.22, 5.95, "In-array\nXNOR-popcount",
        ha="center", va="center", fontsize=10, color=PURPLE_DEEP, fontweight="bold")
ax.text(2.22, 4.65, r"$z_i^{(t)} = \sum_j w_{ij}^{(t)}\,x_j$",
        ha="center", va="center", fontsize=10.5, color="black")
ax.text(2.22, 3.48, "Bitline current summed\nin-array (no ADC per sample);\ninput activations $x_j$",
        ha="center", va="center", fontsize=8.2, color=GRAY_EDGE, style="italic",
        linespacing=1.45)
ax.text(2.22, 1.88, r"XNOR: $1\!\oplus\!1=1,\ 0\!\oplus\!1=0$",
        ha="center", va="center", fontsize=8.5, color=GRAY_EDGE)
ax.text(2.22, 0.88, "single cycle per sample",
        ha="center", va="center", fontsize=8.0, color=GRAY_EDGE, style="italic")

# ── Arrow block 3 → block 4 ────────────────────────────────────────────────
ax.annotate("", xy=(5.18, 3.42), xytext=(4.28, 3.42),
            arrowprops=dict(arrowstyle="-|>", color=GRAY_EDGE, lw=1.5,
                            mutation_scale=14))

# ── Block 4: temporal aggregation ─────────────────────────────────────────
rbox(ax, (5.28, 0.35), 4.55, 6.08, PURPLE_FAINT)

ax.text(7.55, 5.95, "Temporal\naggregation",
        ha="center", va="center", fontsize=10, color=PURPLE_DEEP, fontweight="bold")
ax.text(7.55, 4.60, r"$\hat{z}_i = \dfrac{1}{T}\sum_{t=1}^{T} z_i^{(t)}$",
        ha="center", va="center", fontsize=11, color="black")
ax.text(7.55, 3.30, r"CLT:  $\hat{z}_i \to \mu_i$",
        ha="center", va="center", fontsize=9.0, color=GRAY_EDGE)
ax.text(7.55, 2.42, r"$\mu_i = \sum_j (2p_{ij}-1)\,x_j$",
        ha="center", va="center", fontsize=8.5, color=GRAY_EDGE)
ax.text(7.55, 1.50, r"error $\propto O(1\!/\!\sqrt{T})$",
        ha="center", va="center", fontsize=8.0, color=GRAY_EDGE, style="italic")
ax.text(7.55, 0.68, "digital counter + right-shift",
        ha="center", va="center", fontsize=7.8, color=GRAY_EDGE, style="italic")

# ── Loopback arrow: Block 4 → Block 3 (T-cycle feedback) ──────────────────
ax.annotate("",
            xy=(4.20, 0.26), xytext=(5.30, 0.26),
            arrowprops=dict(arrowstyle="<|-", color=ACCENT, lw=1.4,
                            mutation_scale=12))
ax.text(4.74, -0.08, r"repeat for $T$ sampling cycles",
        fontsize=8.5, color=ACCENT, ha="center", style="italic")

# ─────────────────────────────────────────────────────────────────────────────
#  Inter-panel arrow: right edge of ax00  →  left edge of ax01
# ─────────────────────────────────────────────────────────────────────────────
con = ConnectionPatch(
    xyA=(1.0, 0.48), coordsA=ax00.transAxes,
    xyB=(0.0, 0.48), coordsB=ax01.transAxes,
    arrowstyle="-|>", color=GRAY_EDGE, lw=2.2,
    mutation_scale=18, clip_on=False)
fig.add_artist(con)

# ─────────────────────────────────────────────────────────────────────────────
#  Bottom-left [1,0]:  Spatial tiling — conventional CIM
# ─────────────────────────────────────────────────────────────────────────────
ax = ax10
ax.set_xlim(0, 10);  ax.set_ylim(0, 8.2)
ax.axis("off")
ax.set_title(r"Spatial tiling:  $W\!\in\!\{\pm1\}^{1024\times 1024}$,"
             r"  sub-array $256\!\times\!256$",
             fontsize=10.5, pad=8)

# 4×4 tile grid
tile_n = 4
ox, oy = 0.45, 1.35
side   = 5.6
cell   = side / tile_n
for i in range(tile_n):
    for j in range(tile_n):
        x0 = ox + j * cell
        y0 = oy + i * cell
        color = PURPLE_LIGHT if (i + j) % 2 == 0 else PURPLE_MID
        t = patches.Rectangle((x0, y0), cell * 0.91, cell * 0.91,
                               facecolor=color, edgecolor=PURPLE_DEEP,
                               linewidth=0.8, alpha=0.92)
        ax.add_patch(t)
# Tile count annotation inside one cell
ax.text(ox + cell/2, oy + cell*(tile_n - 0.5),
        r"$\times 16$", ha="center", va="center",
        fontsize=9, color=PURPLE_DEEP, fontweight="bold")

# Aggregation node
agg_pos = (8.25, 3.80)
ac = patches.Circle(agg_pos, 0.52, facecolor="white",
                    edgecolor=ACCENT, linewidth=1.6)
ax.add_patch(ac)
ax.text(agg_pos[0], agg_pos[1], r"$\Sigma$",
        ha="center", va="center", fontsize=14, color=ACCENT, fontweight="bold")

# Arrows: 4 corners → Σ
for (ti, tj) in [(0, tile_n-1), (tile_n-1, tile_n-1), (0, 0), (tile_n-1, 0)]:
    xs = ox + tj * cell + cell * 0.455
    ys = oy + ti * cell + cell * 0.455
    ax.annotate("", xy=(agg_pos[0] - 0.52, agg_pos[1]),
                xytext=(xs, ys),
                arrowprops=dict(arrowstyle="-|>", color=ACCENT,
                                lw=0.7, mutation_scale=9, alpha=0.55,
                                connectionstyle="arc3,rad=-0.08"))

ax.text(8.25, 2.62, "partial-sum\naggregation\n+ ADC/DAC",
        ha="center", va="center", fontsize=8.2, color=ACCENT, linespacing=1.4)

# Bottom stats
ax.text(0.45, 0.85,
        r"Tiles: $\lceil 1024/256 \rceil^{2} = 16$",
        fontsize=9.0, color=GRAY_EDGE)
ax.text(0.45, 0.28,
        r"Inter-tile traffic $\propto$ 16 partial sums per cycle",
        fontsize=8.5, color=GRAY_EDGE)

# ─────────────────────────────────────────────────────────────────────────────
#  Bottom-right [1,1]:  Temporal unfolding — PBNN approach
# ─────────────────────────────────────────────────────────────────────────────
ax = ax11
ax.set_xlim(0, 10);  ax.set_ylim(0, 8.2)
ax.axis("off")
ax.set_title(r"Temporal unfolding:  single array,  draw $T$ stochastic samples",
             fontsize=10.5, pad=8)

# Single sub-array schematic
sx, sy, sw, sh = 0.35, 2.15, 4.3, 5.0
subarray = patches.Rectangle((sx, sy), sw, sh,
                             facecolor=PURPLE_FAINT,
                             edgecolor=PURPLE_DEEP, linewidth=1.4)
ax.add_patch(subarray)

# Grid lines
n_g = 8
for i in range(1, n_g):
    ax.plot([sx, sx+sw], [sy+i*sh/n_g]*2, color=PURPLE_DEEP, lw=0.38, alpha=0.38)
    ax.plot([sx+i*sw/n_g]*2, [sy, sy+sh], color=PURPLE_DEEP, lw=0.38, alpha=0.38)

# sMTJ cell dots
rng = np.random.default_rng(42)
for i in range(1, n_g):
    for j in range(1, n_g):
        if rng.random() < 0.55:
            ax.plot(sx + j*sw/n_g, sy + i*sh/n_g,
                    "o", ms=2.8, color=PURPLE_DEEP, alpha=0.88)

ax.text(sx + sw/2, sy - 0.42,
        r"single $256\times256$ sub-array  (sMTJ cells)",
        ha="center", fontsize=8.5, color=PURPLE_DEEP, fontweight="bold")

# Arrow from array to bitstream area
ax.annotate("", xy=(5.2, sy + sh*0.85),
            xytext=(sx + sw, sy + sh*0.80),
            arrowprops=dict(arrowstyle="-|>", color=ACCENT,
                            lw=1.15, mutation_scale=12, alpha=0.9))

# ── Bitstream rows (larger cells, more spacing) ────────────────────────────
bs_data = [
    [1, 0, 1, 1, 0, 1, 0, 1],
    [1, 1, 0, 1, 0, 0, 1, 1],
    [0, 1, 1, 0, 1, 1, 0, 1],
]
ts_labels = [r"$t\!=\!1$", r"$t\!=\!2$", r"$t\!=\!T$"]
BX, BY   = 5.28, 7.45       # top-left of first bitstream row
box_w, box_h = 0.50, 0.49   # cell size
col_gap, row_gap = 0.07, 0.72

for row, (bs, lab) in enumerate(zip(bs_data, ts_labels)):
    y0 = BY - row * row_gap
    # label
    ax.text(BX - 0.60, y0 + box_h/2, lab,
            fontsize=9.0, color=GRAY_EDGE, va="center", ha="right")
    for k, b in enumerate(bs):
        x0 = BX + k * (box_w + col_gap)
        fc = PURPLE_DEEP if b else "white"
        tc = "white"  if b else PURPLE_DEEP
        rect = patches.Rectangle((x0, y0), box_w, box_h,
                                  facecolor=fc, edgecolor=PURPLE_DEEP, lw=0.75)
        ax.add_patch(rect)
        ax.text(x0 + box_w/2, y0 + box_h/2, str(b),
                ha="center", va="center", fontsize=8.0, color=tc)

# Ellipsis between row 2 and row T
ax.text(BX + 4*(box_w+col_gap), BY - 1.5*row_gap + box_h/2,
        r"$\vdots$", fontsize=13, color=GRAY_EDGE, ha="center", va="center")

# ── Aggregation box ────────────────────────────────────────────────────────
ABX, ABY, ABW, ABH = 5.08, 3.50, 4.72, 1.95
agg_box = FancyBboxPatch((ABX, ABY), ABW, ABH,
                         boxstyle="round,pad=0.07",
                         facecolor="white", edgecolor=PURPLE_DEEP, lw=1.15)
ax.add_patch(agg_box)
ax.text(ABX + ABW/2, ABY + ABH*0.68,
        r"$\hat{z}_i = \frac{1}{T}\sum_{t=1}^{T} z_i^{(t)}$",
        ha="center", va="center", fontsize=10.5, color="black")
ax.text(ABX + ABW/2, ABY + ABH*0.22,
        "digital counter  +  right-shift",
        ha="center", va="center", fontsize=8.2, color=GRAY_EDGE, style="italic")

# Arrow: bitstream rows → aggregation box
ax.annotate("", xy=(ABX + ABW/2, ABY + ABH),
            xytext=(ABX + ABW/2, BY - 2.2*row_gap),
            arrowprops=dict(arrowstyle="-|>", color=PURPLE_DEEP,
                            lw=1.05, mutation_scale=11, alpha=0.82))

# ── Bottom stats ───────────────────────────────────────────────────────────
ax.text(0.35, 0.82,
        r"Tiles needed: $\mathbf{1}$",
        fontsize=9, color=ACCENT, fontweight="bold")
ax.text(0.35, 0.28,
        r"Cycles: $T$ (typ. 10–50);  no inter-tile traffic",
        fontsize=8.5, color=GRAY_EDGE)

# ─────────────────────────────────────────────────────────────────────────────
out = "fig_space_time.png"
plt.savefig(out, dpi=220, bbox_inches="tight")
print(f"saved {out}")
