#!/usr/bin/env python3
"""Phase 4 figure: plot the SAME-FLOW reproduction comparison from comparison_results.json.

Turns the apples-to-apples reproduction results (run comparison_driver.py first) into three
quantitative panels -- the real replacement for the retired fabricated scatter. Raw, UNNUMBERED
panels to figures/ (the deck adds (a)(b)(c)/numbers per the figure norm); nothing invented, every
value read from comparison_results.json. Headless matplotlib (no GUI, no WSL).

Run: python eda/design_survey/plot_comparison.py   (after comparison_driver.py)
"""
from __future__ import annotations
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIGS = REPO / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
PURPLE, RED, DEEP, GREEN, GOLD = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#D4A017"
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3})

d = json.loads((HERE / "comparison_results.json").read_text(encoding="utf-8"))


def _ours_color(is_ours):
    return RED if is_ours else PURPLE


def plot_readout_sa(ax):
    # The three offsets are within MC noise of each other (~0.39), so bars from zero
    # read as flat. A zoomed point plot with +/-1 s.e. error bars (s.e. of an estimated
    # std = sigma/sqrt(2(N-1))) shows the small means AND that they overlap -> the honest
    # "indistinguishable" message, not a fabricated gap.
    rows = d["readout_sa"]["designs"]
    vals = [r["sigma_offset_over_VT"] for r in rows]
    se = [v / (2 * (r["N"] - 1)) ** 0.5 for v, r in zip(vals, rows)]
    xs = list(range(len(rows)))
    short = {"double_tail": "double\ntail", "current_sampling": "current\nsampling",
             "dong_autozero": "auto-zero\n(single-cap)"}
    for i, r in enumerate(rows):
        ours = r.get("is_ours")
        ax.errorbar(i, vals[i], yerr=se[i], fmt=("D" if ours else "o"),
                    color=_ours_color(ours), ms=10, capsize=5, elinewidth=1.5,
                    mec="black", mew=0.8, zorder=3)
        ax.annotate(f"{vals[i]:.3f}", (i, vals[i]), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=8.5,
                    fontweight="bold" if ours else "normal")
    ax.set_xticks(xs)
    ax.set_xticklabels([short.get(r["design"], r["design"]) for r in rows], fontsize=8.5)
    ax.set_xlim(-0.5, len(rows) - 0.5)
    lo, hi = min(v - s for v, s in zip(vals, se)), max(v + s for v, s in zip(vals, se))
    pad = (hi - lo) * 0.55
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_ylabel(r"input-referred offset  $\sigma_\mathrm{off}/V_T$")
    ax.set_title("Readout SA comparator")


def plot_write_dac(ax):
    rows = d["write_dac"]["designs"]
    labels = [r["topology"].replace("_", "\n") for r in rows]
    vals = [r["INL_LSB"] for r in rows]
    cols = [GREEN if r["monotonic"] else "0.6" for r in rows]
    ax.bar(labels, vals, color=cols, edgecolor="black", linewidth=0.7)
    for i, r in enumerate(rows):
        tag = "monotonic" if r["monotonic"] else "non-monotonic"
        ax.text(i, r["INL_LSB"] + 0.05, f"{r['INL_LSB']:.2f}\n{tag}", ha="center", fontsize=8,
                color=GREEN if r["monotonic"] else RED,
                fontweight="bold" if r.get("is_ours") else "normal")
    ax.axhline(1.0, color=GOLD, ls="--", lw=1, label="1 LSB")
    ax.set_ylabel("INL (LSB) into 776 $\\Omega$ write load")
    ax.set_title("Write DAC")
    ax.set_ylim(0, max(vals) * 1.3)
    ax.legend(fontsize=8, loc="upper left")


def plot_sar(ax):
    rows = d["sar_adc"]["designs"]
    labels = [r["scheme"] for r in rows]
    capdac = [r["E_capdac_fJ"] for r in rows]
    comp = [r["E_comp_fJ"] for r in rows]
    x = range(len(rows))
    ax.bar(x, comp, color=DEEP, edgecolor="black", linewidth=0.7, label="comparator (extracted)")
    ax.bar(x, capdac, bottom=comp, color=GOLD, edgecolor="black", linewidth=0.7,
           label="cap-DAC (transient)")
    for i, r in enumerate(rows):
        ax.text(i, r["E_total_fJ"] + 12, f"{r['E_total_fJ']:.0f} fJ", ha="center", fontsize=8.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels)
    ax.set_ylabel("energy per conversion (fJ)")
    ax.set_title(f"SAR readout ({rows[0]['b']}-bit)")
    y_top = max(r["E_total_fJ"] for r in rows) * 1.2
    ax.set_ylim(0, y_top)
    ax.legend(fontsize=8, loc="upper right")
    # tapered improvement arrow: thin at the worse scheme, growing to the better one
    import numpy as np
    x0, y0 = 0.30, (rows[0]["E_total_fJ"] + 60) / y_top
    x1, y1 = 0.70, (rows[1]["E_total_fJ"] + 60) / y_top
    w0, w1, head_l, head_w = 0.006, 0.032, 0.055, 0.066
    p0, p1 = np.array([x0, y0]), np.array([x1, y1])
    u = (p1 - p0) / np.hypot(*(p1 - p0)); nrm = np.array([-u[1], u[0]])
    ph = p1 - u * head_l
    pts = [p0 + nrm * w0 / 2, ph + nrm * w1 / 2, ph + nrm * head_w / 2, p1,
           ph - nrm * head_w / 2, ph - nrm * w1 / 2, p0 - nrm * w0 / 2]
    ax.add_patch(plt.Polygon(pts, closed=True, transform=ax.transAxes,
                             facecolor=GREEN, edgecolor="none", alpha=0.9, zorder=5))
    dpct = (1 - rows[1]["E_total_fJ"] / rows[0]["E_total_fJ"]) * 100
    ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.10, "−%.0f%%" % dpct,
            transform=ax.transAxes, ha="center", fontsize=11, color=GREEN,
            fontweight="bold")


def main():
    specs = [("cmp_readout_sa", plot_readout_sa), ("cmp_write_dac", plot_write_dac),
             ("cmp_sar_energy", plot_sar)]
    for stem, fn in specs:                                   # individual raw panels
        fig, ax = plt.subplots(figsize=(5.0, 4.2))
        fn(ax); fig.tight_layout()
        fig.savefig(FIGS / f"{stem}.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))      # combined 1x3 preview
    for ax, (_, fn) in zip(axes, specs):
        fn(ax)
    fig.tight_layout()
    fig.savefig(FIGS / "cmp_quantitative_1x3.png", dpi=200, bbox_inches="tight"); plt.close(fig)
    print("wrote figures/cmp_readout_sa.png, cmp_write_dac.png, cmp_sar_energy.png, cmp_quantitative_1x3.png")


if __name__ == "__main__":
    main()
