#!/usr/bin/env python3
"""Conceptual contrast of the two SAR cap-DAC switching schemes compared in the EDA study:

  conventional (tentative set-and-down): every bit trial first drives the tested bottom plate UP
      to Vref (a tentative '1'); the comparator then either KEEPS it (decision 1) or pulls it back
      DOWN to gnd (decision 0). The up-then-conditional-down edges on the higher-weight caps are
      the classic wasted tentative charge that dominates the switching energy.

  monotonic (set-and-down / Liu 2010): the array is sampled ONCE with all bottom plates at Vref;
      each trial then ONLY pulls one sub-array DOWN (or leaves it) -- no up-transitions, no
      tentative MSB pre-charge -- so far less charge is drawn from Vref.

The figure is purely illustrative of WHY monotonic dissipates less switching energy; the only
quantitative claims are the transient-measured b=8 cap-DAC switching energies, taken verbatim from
eda/testbenches/sar_capdac_tran_summary.json (b=8 rows, read at runtime).

Headless render of the raw plot to figures/sar_capdac_switching.{png,svg};
the AppendixD deck overlays the (a)(b) letters and exports AppendixD_08.png.
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- article palette ----
PURPLE = "#5E3F8C"
RED    = "#A82038"
GREEN  = "#1A6B5A"
LILAC  = "#C99FD4"
GOLD   = "#D4A017"
SLATE  = "#9580BD"

# ---- measured b=8 cap-DAC switching energies: read from the committed summary at
# runtime (never hardcode -- a stale copy of these numbers once survived a re-run) ----
import json
_SUMMARY = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "testbenches", "sar_capdac_tran_summary.json")
_rows = {r["scheme"]: r for r in json.load(open(_SUMMARY, encoding="utf-8"))["rows"] if r["b"] == 8}
E_CONV_fJ = round(_rows["conventional"]["E_capdac_fJ_measured"], 1)
E_MONO_fJ = round(_rows["monotonic"]["E_capdac_fJ_measured"], 1)
NBITS = 4   # bottom-plate trajectories drawn for the four highest-weight (MSB..) caps; illustrative

plt.rcParams.update({
    "font.size": 11,
    "font.family": "sans-serif",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.edgecolor": "#444444",
    "svg.fonttype": "none",
})

# imposed decision pattern (MSB first) used purely to draw a representative trajectory:
# 1,0,1,0  -> shows both a "kept" bit and a "pulled-down" bit in each scheme.
DECISION = [1, 0, 1, 0]
WEIGHTS = ["MSB (8C)", "4C", "2C", "LSB (1C)"]
TRACE_C = [PURPLE, RED, GREEN, GOLD]


def _lane_offset(bit, n):
    """MSB drawn at the TOP lane, LSB at the bottom."""
    return (n - 1 - bit) * 1.35


def draw_conventional(ax):
    """Per-bit bottom-plate trajectory: each trial sets the tested plate UP to Vref, then the
    decision keeps it (1) or pulls it back DOWN to gnd (0). Higher plates already decided are held.
    Time axis = SAR trial index; y = normalised bottom-plate voltage (0=gnd, 1=Vref)."""
    n = NBITS
    # phases: 0=sample(reset to gnd) then trials 1..n then a final resolve column
    xs = list(range(n + 2))            # 0..n+1  (sample, trial1..n, resolve)
    for bit in range(n):
        v = [0.0]                      # phase 0: reset to gnd
        for k in range(1, n + 2):
            trial = k - 1              # trial index 0..n (k=n+1 is the resolve hold)
            if k <= n:
                if trial < bit:
                    val = float(DECISION[trial])      # already-decided higher bit, held
                elif trial == bit:
                    val = 1.0                          # tentative set-to-Vref (the UP edge)
                else:
                    val = 0.0                          # untested -> gnd
            else:
                val = float(DECISION[bit])             # final resolved state
            v.append(val)
        off = _lane_offset(bit, n)                     # vertical lane per bit (MSB top)
        yv = [off + 0.95 * y for y in v]
        ax.step(xs, yv, where="post", color=TRACE_C[bit], lw=2.4, solid_capstyle="round")
        # baseline (gnd) and rail (Vref) guides for this lane
        ax.axhline(off, xmin=0.04, xmax=0.96, color="#bbbbbb", lw=0.7, zorder=0)
        ax.text(-0.22, off + 0.48, WEIGHTS[bit], ha="right", va="center",
                fontsize=9.5, color=TRACE_C[bit], fontweight="bold")
    # mark one wasted tentative-then-down round trip (a decision-0 bit: tentative UP then DOWN)
    bit0 = next(b for b in range(n) if DECISION[b] == 0)
    off = _lane_offset(bit0, n)
    xtrial = bit0 + 1
    ax.annotate("tentative UP\nthen pulled DOWN\n(wasted charge)",
                xy=(xtrial + 0.5, off + 0.95), xytext=(xtrial + 1.15, off + 0.55),
                fontsize=8.0, color=RED, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.3))
    _finish_axis(ax, n, "Conventional (Tentative Set-and-Down)", E_CONV_fJ, RED)


def draw_monotonic(ax):
    """Set-and-down: sample ALL plates to Vref once (phase 0), then each trial only ever pulls one
    sub-array DOWN to gnd (decision 0) or leaves it at Vref (decision 1). No up-transitions."""
    n = NBITS
    xs = list(range(n + 2))            # 0=sample(all Vref), trials 1..n, hold
    for bit in range(n):
        v = [1.0]                      # phase 0: sampled to Vref
        for k in range(1, n + 2):
            trial = k - 1
            if k <= n:
                if trial < bit:
                    val = float(DECISION[trial])      # earlier bit: down if decided 0
                elif trial == bit:
                    val = float(DECISION[bit])         # this bit: pull DOWN iff decision 0
                else:
                    val = 1.0                          # untested still sampled at Vref
            else:
                val = float(DECISION[bit])
            v.append(val)
        off = _lane_offset(bit, n)
        yv = [off + 0.95 * y for y in v]
        ax.step(xs, yv, where="post", color=TRACE_C[bit], lw=2.4, solid_capstyle="round")
        ax.axhline(off, xmin=0.04, xmax=0.96, color="#bbbbbb", lw=0.7, zorder=0)
        ax.text(-0.22, off + 0.48, WEIGHTS[bit], ha="right", va="center",
                fontsize=9.5, color=TRACE_C[bit], fontweight="bold")
    # mark a single down edge (no up edges at all -> no tentative pre-charge)
    bit0 = next(b for b in range(n) if DECISION[b] == 0)
    off = _lane_offset(bit0, n)
    xtrial = bit0 + 1
    ax.annotate("single DOWN edge\n(no tentative UP)",
                xy=(xtrial, off + 0.95 * 0.5), xytext=(xtrial + 0.7, off + 0.55),
                fontsize=8.0, color=GREEN, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.3))
    _finish_axis(ax, n, "Monotonic (Sample-to-Vref then Down-Only)", E_MONO_fJ, GREEN)


def _finish_axis(ax, n, title, e_fJ, e_color):
    ax.set_title(title, fontsize=11, fontweight="bold", color=PURPLE, pad=10)
    ax.set_xlabel("SAR Trial Index", fontsize=10.5)
    ax.set_ylabel("Cap-DAC Bottom-Plate Voltage (per bit)", fontsize=10.5)
    ax.set_xlim(-1.15, n + 1.7)
    ax.set_ylim(-1.05, (n - 1) * 1.35 + 1.7)
    ax.set_xticks(list(range(n + 2)))
    ax.set_xticklabels(["sample"] + [str(k) for k in range(1, n + 1)] + ["hold"], fontsize=8.5)
    ax.set_yticks([])
    ax.grid(axis="x", alpha=0.3)
    ax.grid(axis="y", alpha=0.0)
    # gnd / Vref reference for the bottom (LSB) lane as a legend-ish hint
    ax.text(-1.08, 0.02, "gnd", fontsize=8, color="#888888", va="center")
    ax.text(-1.08, 0.95, "Vref", fontsize=8, color="#888888", va="center")
    # measured energy annotation box (bottom-centre, clear of the MSB-top trace)
    ax.text(0.5, 0.045,
            f"Measured cap-DAC switching (b = 8): {e_fJ:.1f} fJ",
            transform=ax.transAxes, ha="center", va="bottom", fontsize=10,
            fontweight="bold", color=e_color,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=e_color, lw=1.4, alpha=0.95))


def main():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12.2, 5.4))
    draw_conventional(axL)
    draw_monotonic(axR)

    fig.suptitle("SAR Cap-DAC Switching Schemes: Why Monotonic Switching Saves Energy",
                 fontsize=12.5, fontweight="bold", color=PURPLE, y=0.995)
    # ratio caption under the figure (derived only from the two committed numbers)
    ratio = E_CONV_fJ / E_MONO_fJ
    fig.text(0.5, 0.015,
             f"Conventional draws repeated up-then-down charge on every bit trial; monotonic "
             f"draws charge in down-only steps, reducing cap-DAC switching energy "
             f"{ratio:.2f}x at b = 8 ({E_CONV_fJ:.1f} fJ vs {E_MONO_fJ:.1f} fJ).",
             ha="center", va="bottom", fontsize=9.5, color="#333333")

    fig.tight_layout(rect=(0, 0.045, 1, 0.96))

    # Write the raw, unlettered plot to figures/; the AppendixD deck overlays
    # the (a)(b) panel letters and exports the numbered article/figs/AppendixD_08.png
    # (panel letters live in the deck, never baked into the plot).
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.normpath(os.path.join(here, "..", "..", "..", "figures"))
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, "sar_capdac_switching.png")
    svg = os.path.join(out_dir, "sar_capdac_switching.svg")
    fig.savefig(png, dpi=200)
    fig.savefig(svg)
    plt.close(fig)
    print("wrote", png)
    print("wrote", svg)


if __name__ == "__main__":
    main()
