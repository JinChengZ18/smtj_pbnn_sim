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


def _wrap(s, n=22):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return "\n".join(out)


def plot_submodule(key, fd, ax):
    pts = fd["points"]
    xs = [p["x"] for p in pts]
    xmid = 0.5 * (min(xs) + max(xs))
    for p in pts:
        ours = bool(p.get("is_ours"))
        ax.scatter(p["x"], p["y"], s=190 if ours else 90,
                   marker="*" if ours else "o",
                   c=RED if ours else PURPLE, edgecolor="black",
                   linewidth=1.1 if ours else 0.7, zorder=4 if ours else 3,
                   alpha=0.95 if ours else 0.8)
    # label points; flip to the left for right-side points so text never clips
    for i, p in enumerate(pts):
        ours = bool(p.get("is_ours"))
        dy = 11 if (i % 2 == 0) else -17
        right = p["x"] > xmid
        ax.annotate(_wrap(p["label"]), (p["x"], p["y"]),
                    textcoords="offset points",
                    xytext=(-9 if right else 9, dy),
                    ha="right" if right else "left",
                    fontsize=7.2, color=RED if ours else "0.25",
                    fontweight="bold" if ours else "normal",
                    zorder=5)
    if LOGY.get(key):
        ax.set_yscale("log")
    ax.set_xlabel(fd["x_label"], fontsize=9)
    ax.set_ylabel(fd["y_label"], fontsize=9)
    ax.set_title(TITLE.get(key, key))
    ax.margins(0.22)


def main():
    survey = json.loads(DATA.read_text(encoding="utf-8"))
    for sm in survey["submodules"]:
        key = sm["key"]
        fd = json.loads(sm["compare"]["figure_data"])
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        plot_submodule(key, fd, ax)
        # legend proxy
        ax.scatter([], [], marker="*", s=190, c=RED, edgecolor="black", label="our design")
        ax.scatter([], [], marker="o", s=90, c=PURPLE, edgecolor="black", label="published designs")
        ax.legend(loc="best", fontsize=8.5, framealpha=0.9)
        fig.tight_layout()
        out = OUT / f"design_cmp_{key}.png"
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        print("wrote", out.relative_to(REPO))


if __name__ == "__main__":
    main()
