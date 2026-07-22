"""29b -- Redraw the echo-state phase planes of experiment 29 for the thesis.

Experiment 29 writes ``phase.csv`` / ``phase_dt.csv`` with every quantity the
figure needs, so the thesis version of the plot is a pure re-render of the
canonical run: no recomputation, no risk of drift between the numbers quoted
in the text and the numbers drawn. Relative to the in-experiment plot this
version labels the three criterion lines and the two operating points ON the
axes (the project's figure convention forbids legend text in titles) and uses
the article font size.

Outputs:
  figures/29_esp_certification.png   (overwritten)

Run from the repo root:

    python experiments/29b_esp_replot.py [run_dir]
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
DEFAULT_RUN = REPO / "runs" / "29_esp_cert_20260713_005835"
RATE_TH = -1e-4                      # matches experiments/29_esp_certification.py


def grid_from(path: Path, ycol: str, yscale: float = 1.0):
    """Read one phase CSV into (x, y, {column: 2-D array})."""
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    xs = sorted({float(r["rho_eff"]) for r in rows})
    ys = sorted({float(r[ycol]) for r in rows})
    ix = {v: i for i, v in enumerate(xs)}
    iy = {v: i for i, v in enumerate(ys)}
    out = {k: np.full((len(ys), len(xs)), np.nan)
           for k in ("cert_L", "lin_rho", "mf_rate")}
    for r in rows:
        i, j = iy[float(r[ycol])], ix[float(r["rho_eff"])]
        for k in out:
            out[k][i, j] = float(r[k])
    return np.array(xs), np.array(ys) * yscale, out


def main() -> None:
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_RUN
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 13})

    rho, vb, A = grid_from(run / "phase.csv", "v_bias_V", 1e3)
    rho2, dt, B = grid_from(run / "phase_dt.csv", "dt_s", 1e9)
    levels = np.linspace(-0.05, 0.005, 23)
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))

    def panel(ax, x, y, D, ylab, logy=False):
        cs = ax.contourf(x, y, np.clip(D["mf_rate"], -0.05, 0.005),
                         levels=levels, cmap="viridis")
        ax.contour(x, y, D["cert_L"], levels=[1.0], colors="#A82038",
                   linewidths=2.4)
        ax.contour(x, y, D["lin_rho"], levels=[1.0], colors="#FFD166",
                   linewidths=2.4)
        ax.contour(x, y, D["mf_rate"], levels=[RATE_TH], colors="white",
                   linewidths=1.8, linestyles="--")
        if logy:
            ax.set_yscale("log")
        ax.set_xlabel(r"effective spectral radius $\rho_\mathrm{eff}$")
        ax.set_ylabel(ylab)
        return cs

    ax = axes[0]
    cs = panel(ax, rho, vb, A, r"$V_\mathrm{bias}$ (mV)")
    ax.plot([0.9], [0.0], marker="*", ms=17, color="white", mec="black",
            mew=0.8, clip_on=False)
    ax.plot([0.5], [0.0], marker="o", ms=10, color="white", mec="black",
            mew=0.8, clip_on=False)
    ax.annotate("default\noperating point", xy=(0.9, 0.0), xytext=(1.06, 16),
                fontsize=11, color="white",
                arrowprops=dict(arrowstyle="-", color="white", lw=1.2))
    ax.annotate("hardware-evaluation\noperating point", xy=(0.5, 0.0),
                xytext=(0.14, 22), fontsize=11, color="white",
                arrowprops=dict(arrowstyle="-", color="white", lw=1.2))
    ax.text(0.115, 108, "row-wise\nsufficient bound", color="#A82038",
            fontsize=11.5, fontweight="bold", va="top")
    ax.text(0.99, 108, "linearised\nspectral criterion", color="#FFD166",
            fontsize=11.5, fontweight="bold", va="top")
    ax.text(1.55, 86, "contraction\nboundary", color="white", fontsize=11.5,
            fontweight="bold", va="top")
    ax.set_title("bias plane at dt = 8 ns")

    ax = axes[1]
    panel(ax, rho2, dt, B, "reservoir step dt (ns)", logy=True)
    ax.plot([0.9], [8.0], marker="*", ms=17, color="white", mec="black",
            mew=0.8)
    ax.plot([0.5], [25.0], marker="o", ms=10, color="white", mec="black",
            mew=0.8)
    ax.text(0.115, 1.35, "row-wise\nsufficient bound", color="#A82038",
            fontsize=11.5, fontweight="bold", va="bottom")
    ax.text(1.02, 1.35, "linearised\nspectral criterion", color="#FFD166",
            fontsize=11.5, fontweight="bold", va="bottom")
    ax.text(1.30, 78, "contraction\nboundary", color="white", fontsize=11.5,
            fontweight="bold", va="top")
    ax.text(0.87, 6.2, "default", color="white", fontsize=11, ha="right")
    ax.text(0.53, 25.0, " hardware evaluation", color="white", fontsize=11,
            va="center")
    ax.set_title(r"step-size plane at $V_\mathrm{bias}=0$")

    cb = fig.colorbar(cs, ax=axes, fraction=0.046, pad=0.02)
    cb.set_label("tail decay rate per step (mean field)")
    out = REPO / "figures" / "29_esp_certification.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print(f"replotted {run.name} -> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
