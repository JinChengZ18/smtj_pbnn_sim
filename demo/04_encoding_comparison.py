"""04_encoding_comparison.py — Schematic figure for Experiment 09.

Visualises *why* PBNN survives single-cell faults that wreck digital
MRAM-backed neural networks: the per-cell contribution to a stored
weight is **uniform 1/T** under PBNN's T-cell stochastic encoding, but
**geometric** under conventional N-bit positional MRAM, so the MSB of
the latter is a single point of failure.

Produces a single 2x2 grid PNG.  All math is matplotlib-mathtext
compatible.  Cell counts (T, N) are easy to change at the top of
main().

Run from the repo root:

    python demo/04_encoding_comparison.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------#
PURPLE_DARK   = "#4B1369"
PURPLE_LIGHT  = "#EFE6F4"
ORANGE        = "#D97706"
GRAY_DARK     = "#4B5563"
GRAY_LIGHT    = "#E5E7EB"
PAPER_BG      = "#FFFFFF"


# ---------------------------------------------------------------------------#
# Panel (a): PBNN T-cell encoding (equal widths)                            #
# ---------------------------------------------------------------------------#

def _panel_pbnn(ax, T: int = 8) -> None:
    """T equal-width cells with abstract ±1/T contribution annotations."""
    rng = np.random.default_rng(7)
    samples = np.where(rng.random(T) < 0.6, 1, -1).astype(int)

    cell_w = 1.0
    gap = 0.14
    total = T * cell_w + (T - 1) * gap
    x0 = -total / 2.0

    for i, s in enumerate(samples):
        x = x0 + i * (cell_w + gap)
        face = PURPLE_DARK if s == 1 else PURPLE_LIGHT
        rect = mpatches.FancyBboxPatch(
            (x, -0.55), cell_w, 1.10,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            linewidth=1.8, edgecolor="black", facecolor=face)
        ax.add_patch(rect)
        ax.text(x + cell_w / 2.0, 0.0,
                "+1" if s == 1 else r"$-1$",
                ha="center", va="center", fontsize=18, fontweight="bold",
                color="white" if s == 1 else "black")
        sign = "+" if s == 1 else r"-"
        ax.text(x + cell_w / 2.0, 0.85, fr"${sign}1/T$",
                ha="center", va="bottom", fontsize=14, color=PURPLE_DARK,
                fontweight="bold")
        ax.text(x + cell_w / 2.0, -0.85, fr"$s_{{{i + 1}}}$",
                ha="center", va="top", fontsize=14)

    # Reconstruction equation
    ax.text(0.0, -2.05,
            r"$w \,=\, \dfrac{1}{T}\sum_{i=1}^{T} s_i, "
            r"\quad s_i \in \{-1,\,+1\}$",
            ha="center", va="center", fontsize=18)

    # Headline
    ax.text(0.0, 1.85,
            f"(a)  PBNN with T={T} stochastic cells per weight",
            ha="center", va="bottom", fontsize=16, fontweight="bold",
            color=PURPLE_DARK)
    ax.text(0.0, 1.50,
            r"every cell contributes the same magnitude $1/T$",
            ha="center", va="bottom", fontsize=13, style="italic",
            color="#333")

    pad = 0.4
    ax.set_xlim(x0 - pad, -x0 + pad)
    ax.set_ylim(-2.6, 2.30)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------------------#
# Panel (b): MRAM N-bit positional encoding (geometric widths)              #
# ---------------------------------------------------------------------------#

def _panel_mram(ax, n_bits: int = 8) -> None:
    """N cells with widths proportional to sqrt(2^bit) — visual hint of
    geometric scaling without making LSB cells unreadable."""
    bit_positions = list(range(n_bits - 1, -1, -1))  # MSB on left

    widths_raw = np.array([np.sqrt(2.0 ** p) for p in bit_positions])
    widths = widths_raw / widths_raw.max() * 2.6
    widths = np.maximum(widths, 0.40)

    gap = 0.10
    total = widths.sum() + gap * (n_bits - 1)
    x = -total / 2.0
    cells_x = []
    for w in widths:
        cells_x.append(x)
        x += w + gap

    bit_states = [(p % 2) for p in bit_positions]  # 1,0,1,0,...

    for i, (bx, w, b, pos) in enumerate(zip(cells_x, widths, bit_states,
                                              bit_positions)):
        face = GRAY_DARK if b == 1 else GRAY_LIGHT
        rect = mpatches.FancyBboxPatch(
            (bx, -0.55), w, 1.10,
            boxstyle="round,pad=0.02,rounding_size=0.06",
            linewidth=1.8, edgecolor="black", facecolor=face)
        ax.add_patch(rect)
        ax.text(bx + w / 2.0, 0.0, str(b),
                ha="center", va="center", fontsize=18, fontweight="bold",
                color="white" if b == 1 else "black")
        # 2^bit label above
        if w >= 0.55:
            ax.text(bx + w / 2.0, 0.85, fr"$2^{{{pos}}}$",
                    ha="center", va="bottom", fontsize=13, color=GRAY_DARK,
                    fontweight="bold")
        else:
            ax.text(bx + w / 2.0, 0.85, fr"$2^{{{pos}}}$",
                    ha="center", va="bottom", fontsize=10, color=GRAY_DARK)
        # Cell index below
        ax.text(bx + w / 2.0, -0.85, fr"$b_{{{pos}}}$",
                ha="center", va="top", fontsize=14)

    # MSB callout
    ax.annotate(
        r"MSB carries  $2^{N-1}\!/(2^{N}\!-\!1) \approx 50\%$",
        xy=(cells_x[0] + widths[0] / 2.0, 0.55),
        xytext=(cells_x[0] - 0.15, 1.85),
        fontsize=12, color=ORANGE, fontweight="bold",
        ha="left",
        arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.4))

    # Reconstruction equation
    ax.text(0.0, -2.05,
            r"$w \,=\, \dfrac{\sum_{i=0}^{N-1} b_i \, 2^{i}}{2^{N}-1},"
            r"\quad b_i \in \{0,\,1\}$",
            ha="center", va="center", fontsize=18)

    # Headline
    ax.text(0.0, 2.55,
            f"(b)  Digital MRAM with N={n_bits} positional bits per weight",
            ha="center", va="bottom", fontsize=16, fontweight="bold",
            color=GRAY_DARK)
    ax.text(0.0, 2.20,
            r"each cell contributes $2^{i}$ — geometrically unequal",
            ha="center", va="bottom", fontsize=13, style="italic",
            color="#333")

    pad = 0.4
    ax.set_xlim(cells_x[0] - pad, cells_x[-1] + widths[-1] + pad)
    ax.set_ylim(-2.6, 3.00)
    ax.set_aspect("equal")
    ax.axis("off")


# ---------------------------------------------------------------------------#
# Panel (c): per-cell contribution bar chart (log y)                        #
# ---------------------------------------------------------------------------#

def _panel_contribution(ax, T: int = 8, n_bits: int = 8) -> None:
    pbnn_pct = np.full(T, 100.0 / T)
    mram_pct = np.array([(1 << b) / ((1 << n_bits) - 1) * 100.0
                          for b in range(n_bits)])

    x_pbnn = np.arange(T)
    sep = 1.5
    x_mram = np.arange(n_bits) + T + sep

    ax.bar(x_pbnn, pbnn_pct, width=0.78, color=PURPLE_DARK,
            edgecolor="black", linewidth=0.5,
            label=f"PBNN  (T = {T})")
    ax.bar(x_mram, mram_pct, width=0.78, color=GRAY_DARK,
            edgecolor="black", linewidth=0.5,
            label=f"Digital MRAM  (N = {n_bits})")

    msb_idx = n_bits - 1
    ax.bar([x_mram[msb_idx]], [mram_pct[msb_idx]], width=0.78,
            color=ORANGE, edgecolor="black", linewidth=0.5)
    ax.annotate(
        f"MSB: {mram_pct[msb_idx]:.1f} %\nsingle point of failure",
        xy=(x_mram[msb_idx], mram_pct[msb_idx]),
        xytext=(x_mram[msb_idx] - 1.3, mram_pct[msb_idx] * 1.7),
        ha="right", fontsize=12.5, color=ORANGE, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.4))

    ax.text(np.mean(x_pbnn), 100.0 / T * 1.6, "all equal",
            ha="center", fontsize=13, color=PURPLE_DARK, fontweight="bold")

    ax.set_yscale("log")
    ax.set_ylabel("contribution to dynamic range (%)", fontsize=14)
    ax.set_xticks(np.concatenate([x_pbnn, x_mram]))
    ax.set_xticklabels(
        [fr"$s_{{{i + 1}}}$" for i in range(T)]
        + [fr"$b_{{{i}}}$" for i in range(n_bits)],
        fontsize=12)
    ax.set_title("(c)  Per-cell contribution to the dynamic range",
                  fontsize=15, pad=12, fontweight="bold")
    ax.set_ylim(0.2, 240)
    ax.grid(axis="y", which="both", alpha=0.3, linestyle=":")
    ax.legend(loc="upper left", fontsize=12.5, framealpha=0.95)
    ax.tick_params(axis="y", labelsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ---------------------------------------------------------------------------#
# Panel (d): single-cell-flip impact distribution                           #
# ---------------------------------------------------------------------------#

def _panel_bitflip_impact(ax, T: int = 8, n_bits: int = 8,
                            n_samples: int = 10_000, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    pbnn_impacts = np.full(n_samples, 2.0 / T)
    bit_choices = rng.integers(0, n_bits, size=n_samples)
    mram_impacts = (2.0 * (1 << bit_choices)) / ((1 << n_bits) - 1)

    bins = np.linspace(0, 1.05, 44)
    ax.hist(pbnn_impacts, bins=bins, alpha=0.85,
             weights=np.ones_like(pbnn_impacts) / n_samples * 100,
             color=PURPLE_DARK, edgecolor="black", linewidth=0.4,
             label=f"PBNN  (T = {T})")
    ax.hist(mram_impacts, bins=bins, alpha=0.7,
             weights=np.ones_like(mram_impacts) / n_samples * 100,
             color=GRAY_DARK, edgecolor="black", linewidth=0.4,
             label=f"MRAM  (N = {n_bits})")

    pbnn_max = pbnn_impacts.max()
    mram_max = mram_impacts.max()
    ax.axvline(pbnn_max, color=PURPLE_DARK, linestyle="--",
                linewidth=1.6, alpha=0.75)
    ax.axvline(mram_max, color=ORANGE, linestyle="--",
                linewidth=1.6, alpha=0.85)

    y_top = max(20, ax.get_ylim()[1])
    ax.set_ylim(0, y_top * 1.15)
    y_top = ax.get_ylim()[1]

    ax.text(pbnn_max - 0.02, y_top * 0.82,
            "PBNN bounded\n" + r"at $2/T$",
            color=PURPLE_DARK, fontsize=13, fontweight="bold",
            ha="right", va="top")
    ax.text(mram_max - 0.02, y_top * 0.50,
            "MRAM unbounded\n(full sign flip\nwhen MSB hit)",
            color=ORANGE, fontsize=13, fontweight="bold",
            ha="right", va="top")

    ax.set_xlabel(
        r"normalised weight error $|\Delta w| / w_{\max}$  "
        "after one random cell flip",
        fontsize=14)
    ax.set_ylabel("share of single-flip events (%)", fontsize=14)
    ax.set_xlim(-0.02, 1.10)
    ax.set_title("(d)  Effective weight error from one random cell flip",
                  fontsize=15, pad=12, fontweight="bold")
    ax.legend(loc="upper center", fontsize=12.5, framealpha=0.95)
    ax.tick_params(axis="both", labelsize=11)
    ax.grid(axis="y", alpha=0.3, linestyle=":")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ---------------------------------------------------------------------------#
# Main                                                                      #
# ---------------------------------------------------------------------------#

def main() -> None:
    print("=== Demo 04: PBNN vs digital-MRAM encoding-mapping comparison ===")

    T = 8
    N = 8

    out_dir = REPO / "demo" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 13,
    })

    fig = plt.figure(figsize=(17, 11), facecolor=PAPER_BG)
    gs = fig.add_gridspec(
        2, 2,
        height_ratios=[0.95, 1.05],
        hspace=0.32, wspace=0.20,
        top=0.93, bottom=0.085,
        left=0.05, right=0.97,
    )

    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    _panel_pbnn(ax_a, T=T)
    _panel_mram(ax_b, n_bits=N)
    _panel_contribution(ax_c, T=T, n_bits=N)
    _panel_bitflip_impact(ax_d, T=T, n_bits=N, n_samples=10_000)

    fig.suptitle(
        "How a single weight is mapped to physical cells:  "
        "stochastic PBNN encoding versus positional digital-MRAM encoding",
        fontsize=18, y=0.985, fontweight="bold")

    caption = (
        "PBNN's per-cell weight equality removes the MSB-dominance failure "
        "mode of conventional digital CIM: any single cell flip shifts the "
        r"stored weight by at most $2/T$, regardless of which cell flipped, "
        "while a positional N-bit cell can shift the weight by up to a "
        "full sign flip when the MSB is hit. This is the structural reason "
        "PBNN survives the bit-flip stress sweep in Experiment 09."
    )
    fig.text(0.5, 0.020, caption, ha="center", va="bottom",
              fontsize=12, style="italic",
              bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF8E5",
                        edgecolor="#E0C870", linewidth=1.0))

    out_path = out_dir / "04_encoding_comparison.png"
    fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=PAPER_BG)
    print(f"  Saved: {out_path.relative_to(REPO)}")
    print(f"  Size:  {out_path.stat().st_size / 1024:.0f} KB")
    print("Done.")


if __name__ == "__main__":
    main()
