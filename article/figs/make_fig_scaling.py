"""
fig_scaling_gap  v3 — fixes:
  (a) "410×/2yr" and "2×/2yr" moved to non-overlapping positions with rotation
  (b) remove ugly <-> arrow; replace gap note with clean text box in shaded band
  (c) restore 4 bars (8b MAC / SRAM 8KB / SRAM 1MB / DRAM); remove <-> arrow;
      clean "3200×" annotation in axes-fraction corner
Sources: Horowitz ISSCC 2014; Sze et al. 2020 (energy table); NVIDIA product datasheets
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

PURPLE_DEEP  = "#6E2E83"
PURPLE_MID   = "#9B6AB5"
PURPLE_LIGHT = "#C8A8DA"
PURPLE_FAINT = "#ECDFF2"
GRAY_EDGE    = "#555555"
ACCENT       = "#8B3A62"

mpl.rcParams.update({
    "font.family":       "serif",
    "font.serif":        ["Arial", "Liberation Serif", "DejaVu Serif"],
    "mathtext.fontset":  "stix",
    "axes.edgecolor":    GRAY_EDGE,
    "axes.labelcolor":   "black",
    "axes.linewidth":    0.9,
    "xtick.color":       "black",
    "ytick.color":       "black",
    "xtick.direction":   "in",
    "ytick.direction":   "in",
    "axes.grid":         True,
    "grid.alpha":        0.28,
    "grid.linestyle":    "--",
    "legend.frameon":    True,
    "legend.framealpha": 0.88,
    "legend.edgecolor":  GRAY_EDGE,
})

fig = plt.figure(figsize=(13.5, 4.4))
gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.05, 0.92], wspace=0.36)

# ─────────────────────────────────────────────────────────────────────────────
#  (a)  LLM parameter count vs HBM capacity
# ─────────────────────────────────────────────────────────────────────────────
ax = fig.add_subplot(gs[0, 0])

models = [
    # (year, params_B, label, dx, dy_mult)
    (2018.08, 0.110, "BERT-B",  0.08,  0.50),
    (2018.60, 0.340, "BERT-L",  0.08,  1.80),
    (2019.20, 1.500, "GPT-2",   0.10,  1.22),
    (2020.50, 175.0, "GPT-3",   0.10,  1.20),
    (2021.60, 530.0, "MT-NLG", -1.05,  1.20),
    (2022.40, 540.0, "PaLM",    0.10,  1.20),
    (2024.10, 1800., "GPT-4*", -0.60,  0.52),
]
yrs_m = np.array([m[0] for m in models])
pms   = np.array([m[1] for m in models])

gpus = [
    # (year, GB, label, dx, dy_mult)
    (2017.4,  16,  "V100", 0.10, 1.38),
    (2020.2,  40,  "A100", 0.10, 0.47),
    (2022.8,  80,  "H100", 0.10, 0.44),
    (2024.2, 192,  "B200",-0.68, 1.32),
]
yrs_g = np.array([g[0] for g in gpus])
mems  = np.array([g[1] for g in gpus])

ax.semilogy(yrs_m, pms, "o-", color=PURPLE_DEEP, ms=6.5, lw=1.6,
            label="LLM params (B)", zorder=3)
ax.semilogy(yrs_g, mems, "s--", color=ACCENT, ms=6.5, lw=1.6,
            label="HBM / accelerator (GB)", zorder=3)

for y, p, n, dx, dy in models:
    ax.annotate(n, (y, p), xytext=(y+dx, p*dy),
                fontsize=7.5, color=PURPLE_DEEP, ha="left",
                arrowprops=dict(arrowstyle="-", color=PURPLE_DEEP, lw=0.5, alpha=0.55)
                           if abs(dx) > 0.3 else None)
for y, m, n, dx, dy in gpus:
    ax.annotate(n, (y, m), xytext=(y+dx, m*dy),
                fontsize=7.5, color=ACCENT, ha="left",
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.5, alpha=0.55)
                           if abs(dx) > 0.3 else None)

t = np.linspace(2018, 2025.5, 80)
ax.semilogy(t, 0.15*(410.0**((t-2018)/2)), color=PURPLE_DEEP, lw=0.9, alpha=0.25)
ax.semilogy(t, 16*(2.0**((t-2017.4)/2)), color=ACCENT, lw=0.9, alpha=0.25)

t_fill = np.linspace(2020, 2025.5, 80)
ax.fill_between(t_fill,
                0.15*(410.0**((t_fill-2018)/2)),
                16*(2.0**((t_fill-2017.4)/2)),
                color=PURPLE_FAINT, alpha=0.50, zorder=1)

# Trend-rate labels — placed in clear space, rotated to match trend-line slopes
# Model: ~52° on this log-scale plot; GPU: ~8°
ax.text(2022.5, 5200, r"$410\times / 2\,\mathrm{yr}$",
        color=PURPLE_DEEP, fontsize=9.5, fontweight="bold",
        rotation=52, ha="left", va="bottom")
ax.text(2023.0, 140, r"$2\times / 2\,\mathrm{yr}$",
        color=ACCENT, fontsize=9.5, fontweight="bold",
        rotation=8, ha="left", va="bottom")

ax.set_xlabel("Year", fontsize=10.5)
ax.set_ylabel("Scale (log)", fontsize=10.5)
ax.set_title("Model growth outpaces memory capacity", fontsize=10.5)
ax.set_xlim(2017.2, 2026.5)
ax.set_ylim(0.05, 5e4)
ax.legend(loc="upper left", fontsize=8.5)

# ─────────────────────────────────────────────────────────────────────────────
#  (b)  Real GPU hardware compute–bandwidth asymmetry
#       Sources: NVIDIA official product datasheets (FP16 Tensor Core TFLOPS,
#       HBM bandwidth GB/s, NVLink bidirectional GB/s per GPU)
# ─────────────────────────────────────────────────────────────────────────────
ax = fig.add_subplot(gs[0, 1])

hw_raw = [
    # (year, name, FP16-TC TFLOPS, HBM GB/s, NVLink GB/s per GPU)
    (2016.5, "P100",  21.2,  732, 160),   # Pascal SXM2
    (2017.7, "V100",  125,   900, 300),   # Volta SXM2
    (2020.7, "A100",  312,  2000, 600),   # Ampere SXM4 80 GB
    (2022.8, "H100",  989,  3350, 900),   # Hopper SXM5
    (2024.1, "H200",  989,  4800, 900),   # Hopper H200 SXM
]
yrs_hw  = np.array([r[0] for r in hw_raw])
fl_hw   = np.array([r[2] for r in hw_raw])
bw_hw   = np.array([r[3] for r in hw_raw])
nv_hw   = np.array([r[4] for r in hw_raw])
names_b = [r[1] for r in hw_raw]

fl_n = fl_hw / fl_hw[0]
bw_n = bw_hw / bw_hw[0]
nv_n = nv_hw / nv_hw[0]

ax.semilogy(yrs_hw, fl_n, "o-",  color=PURPLE_DEEP, ms=6.5, lw=1.8, label="FP16 Tensor TFLOPS")
ax.semilogy(yrs_hw, bw_n, "^-",  color=PURPLE_MID,  ms=6.5, lw=1.6, label="HBM bandwidth")
ax.semilogy(yrs_hw, nv_n, "s--", color=ACCENT, ms=6.5, lw=1.6, label="NVLink BW")

ax.fill_between(yrs_hw, bw_n, fl_n, color=PURPLE_LIGHT, alpha=0.28)

lbl_off = {
    "P100": ( 0.13, 1.40),
    "V100": ( 0.13, 1.30),
    "A100": ( 0.13, 0.52),
    "H100": ( 0.13, 1.28),
    "H200": (-0.65, 0.52),
}
for yr, nm, fn in zip(yrs_hw, names_b, fl_n):
    dx, dy = lbl_off[nm]
    ax.annotate(nm, (yr, fn), xytext=(yr+dx, fn*dy),
                fontsize=7.5, color=PURPLE_DEEP, ha="left")

# Clean gap annotation — text box in the shaded band, no arrow
gap_val = fl_n[-2] / bw_n[-2]   # at H100
ax.text(2021.0, 16,
        f"$\\sim\\!{gap_val:.0f}\\times$ divergence\n(FLOPS/HBM at H100)",
        fontsize=8.5, color=GRAY_EDGE, ha="center", va="center",
        bbox=dict(boxstyle="round,pad=0.32", fc="white",
                  ec=GRAY_EDGE, alpha=0.82, lw=0.7))

ax.set_xlabel("Year", fontsize=10.5)
ax.set_ylabel("Normalized capability (P100 = 1)", fontsize=10.5)
ax.set_title("Hardware compute–bandwidth asymmetry", fontsize=10.5)
ax.legend(loc="upper left", fontsize=8.5)
ax.set_xlim(2015.3, 2025.8)
ax.set_ylim(0.7, 400)

# ─────────────────────────────────────────────────────────────────────────────
#  (c)  Horowitz 2014 energy costs — 45 nm, reproduced from Sze et al. (2020)
#       4 bars: 8b MAC / SRAM 8KB / SRAM 1MB (estimated) / DRAM 32b
# ─────────────────────────────────────────────────────────────────────────────
ax = fig.add_subplot(gs[0, 2])

categories = ["8-bit\nMAC", "SRAM\n(8 KB)", "SRAM\n(1 MB)", "DRAM\naccess"]
# pJ @45nm: Horowitz 2014 / Sze et al. 2020; SRAM 1MB ~100 pJ is an estimate
costs      = [0.2, 5, 100, 640]
bar_colors = [PURPLE_DEEP, PURPLE_MID, PURPLE_LIGHT, ACCENT]

xpos = np.arange(len(categories))
bars = ax.bar(xpos, costs, color=bar_colors, edgecolor=GRAY_EDGE,
              lw=0.9, width=0.62)
ax.set_yscale("log")

# Value labels: inside bar for DRAM (white), above bar for others
for b, v in zip(bars, costs):
    cx = b.get_x() + b.get_width() / 2
    if v >= 100:
        ax.text(cx, v * 0.38, f"{v} pJ",
                ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
    else:
        ax.text(cx, v * 2.4, f"{v} pJ",
                ha="center", fontsize=8.5, color="black")

# "3200×" ratio annotation — axes-fraction corner, no crossing arrow
ax.text(0.98, 0.97, r"$3200\times$ (MAC $\to$ DRAM)",
        transform=ax.transAxes, fontsize=9.0, color=GRAY_EDGE,
        fontweight="bold", ha="right", va="top",
        bbox=dict(boxstyle="round,pad=0.32", fc="white",
                  ec=GRAY_EDGE, alpha=0.88, lw=0.7))

ax.set_xticks(xpos)
ax.set_xticklabels(categories, fontsize=9.0)
ax.set_ylabel("Energy per operation (pJ, log)", fontsize=10.0)
ax.set_title("Compute vs data-movement energy", fontsize=10.5)
ax.set_ylim(0.06, 4000)
ax.set_xlim(-0.6, 3.6)
ax.grid(axis="x", visible=False)

# ─────────────────────────────────────────────────────────────────────────────
out = "fig_scaling_gap.png"
plt.savefig(out, dpi=220, bbox_inches="tight")
print(f"saved {out}")
