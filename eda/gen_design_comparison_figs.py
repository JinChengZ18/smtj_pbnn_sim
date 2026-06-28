#!/usr/bin/env python3
"""Submodule design-space comparison figures (literature vs our design).

Reads the committed multi-agent literature survey (eda/design_survey/submodule_survey.json,
real arXiv/OA citations + a two-axis option comparison per submodule) and renders one
comparison scatter per submodule into figures/ (raw, UNNUMBERED -- the numbered article
figures are arranged separately via article/ppt/). Each marker is a published design or
ours, placed on the two quantitative axes most relevant to the sMTJ-PBNN/RC task.

Outputs (figures/, raw):
  design_cmp_readout_sa.png   -- readout sense amplifier: offset/V_T vs energy
  design_cmp_write_dac_ir.png -- write-DAC + IR pre-distortion: residual droop vs circuit completeness
  design_cmp_sar_adc.png      -- column-shared SAR readout: offset/V_T vs comparator energy

Run: python eda/gen_design_comparison_figs.py
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "eda" / "design_survey" / "submodule_survey.json"
OUT = REPO / "figures"
OUT.mkdir(parents=True, exist_ok=True)

RED, PURPLE, GREY = "#A82038", "#5E3F8C", "#8A8A8A"
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.titlesize": 11.5, "figure.dpi": 110})

LOGY = {"readout_sa": True, "write_dac_ir": False, "sar_adc": True}
TITLE = {
    "readout_sa": "Readout SA: input-referred offset vs energy (lit. vs ours)",
    "write_dac_ir": "Write-DAC + IR pre-distortion: remote-row error vs circuit completeness",
    "sar_adc": "Column-shared SAR readout: SA offset vs comparator energy",
}


def _mathify(s):
    """Render subscript tokens as mathtext so axis labels show no raw '_'."""
    s = s.replace("sigma_offset", r"$\sigma_\mathrm{offset}$").replace("V_T", r"$V_T$")
    s = s.replace(" sigma", r" $\sigma$")
    return s


def _short_ref(lbl, ours):
    if ours:
        return "ours"
    w = lbl.replace(",", " ").replace(":", " ").split()
    return f"{w[0]} {w[1]}" if len(w) > 1 and w[1][:2].isdigit() else w[0]


def plot_submodule(key, fd, ax):
    """Numbered markers + a side legend mapping numbers->refs, so labels never overlap."""
    pts = fd["points"]
    for i, p in enumerate(pts, 1):
        ours = bool(p.get("is_ours"))
        ax.scatter(p["x"], p["y"], s=210 if ours else 95, marker="*" if ours else "o",
                   c=RED if ours else PURPLE, edgecolor="black",
                   linewidth=1.1 if ours else 0.7, zorder=4 if ours else 3,
                   alpha=0.95 if ours else 0.85, label=f"{i}. {_short_ref(p['label'], ours)}")
        ax.annotate(str(i), (p["x"], p["y"]), textcoords="offset points", xytext=(5, 4),
                    fontsize=8, color=RED if ours else "0.2", fontweight="bold", zorder=5)
    if LOGY.get(key):
        ax.set_yscale("log")
    ax.set_xlabel(_mathify(fd["x_label"]), fontsize=9)
    ax.set_ylabel(_mathify(fd["y_label"]), fontsize=9)
    ax.set_title(TITLE.get(key, key))
    ax.margins(0.16)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8,
              framealpha=0.9, handletextpad=0.3, labelspacing=0.45, borderpad=0.4)


def main():
    survey = json.loads(DATA.read_text(encoding="utf-8"))
    for sm in survey["submodules"]:
        key = sm["key"]
        fd = json.loads(sm["compare"]["figure_data"])
        fig, ax = plt.subplots(figsize=(9.8, 5.2))
        plot_submodule(key, fd, ax)
        fig.tight_layout()
        out = OUT / f"design_cmp_{key}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("wrote", out.relative_to(REPO))


if __name__ == "__main__":
    main()
