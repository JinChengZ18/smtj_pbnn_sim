#!/usr/bin/env python3
"""Regenerate the EDA co-design analysis figures embedded in Chapters 4-5 (article/figs/).

Reproduces the article figure style (palette + grid/log conventions of experiments/16_*.py) from the
committed result JSONs, so the chapter figures regenerate deterministically. Headless matplotlib
(no GUI). Outputs: Chapter04_local_21 (device dual-model consistency), Chapter04_local_15 (read-out
offset pareto), Chapter04_local_16 (write energy/supply), Chapter05_local_09 (reservoir energy front),
Chapter04_local_17 (IR pre-distortion). The circuit schematics live under eda/hero/schematics/.

Run: python eda/gen_supplement_figs.py
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
TB = REPO / "eda" / "testbenches"
HERO = REPO / "eda" / "hero"
WL = REPO / "eda" / "extraction" / "writeline"
OUT = REPO / "article" / "figs"
FIGDIR = REPO / "figures"
OUT.mkdir(parents=True, exist_ok=True)
# Raw UNNUMBERED per-panel exports (no (a)(b)(c)); the PPT (article/ppt/, via
# eda/build_ppt_figs.py) composes these, adds the panel letters + figure number,
# and exports the numbered figure to article/figs/. See memory: figures carry no
# baked panel letters -- the deck adds them, for portability.
PANELS = REPO / "figures" / "panels"
PANELS.mkdir(parents=True, exist_ok=True)

# Panel (c) of each submodule figure is the quantitative same-flow comparison (ours vs
# the reproduced alternatives), rendered by the design-survey module so there is one
# source of truth. comparison_results.json is produced by comparison_driver.py.
import sys
sys.path.insert(0, str(REPO / "eda" / "design_survey"))
import plot_comparison as cmp


def save_panels(fig, axes, stem):
    """Save each axes of `fig` as its own PNG (no panel letter) to figures/panels/.
    Unions any twin/overlapping axes (e.g. twinx) so secondary labels aren't
    clipped, and clamps each crop horizontally to the mid-gap toward the
    neighbouring subplot so an adjacent axes' spine can't bleed in as a stray
    vertical line at the panel edge."""
    from matplotlib.transforms import Bbox
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    for i, axx in enumerate(axes):
        pos = tuple(round(v, 4) for v in axx.get_position().bounds)
        sibs = [a for a in fig.axes
                if tuple(round(v, 4) for v in a.get_position().bounds) == pos]
        bb = Bbox.union([a.get_tightbbox(rend) for a in sibs])       # display px
        this = Bbox.union([a.get_window_extent(rend) for a in sibs])  # plot area
        left_lim, right_lim = 0.0, float(fig.bbox.width)
        for a in fig.axes:
            if a in sibs:
                continue
            w = a.get_window_extent(rend)
            if w.x1 <= this.x0:                       # neighbour to the left
                left_lim = max(left_lim, 0.5 * (w.x1 + this.x0))
            elif w.x0 >= this.x1:                     # neighbour to the right
                right_lim = min(right_lim, 0.5 * (w.x0 + this.x1))
        exp = bb.expanded(1.06, 1.10)
        exp = Bbox.from_extents(max(exp.x0, left_lim), exp.y0,
                                min(exp.x1, right_lim), exp.y1)
        ext = exp.transformed(fig.dpi_scale_trans.inverted())
        fig.savefig(PANELS / f"{stem}_{'abcdef'[i]}.png", dpi=200, bbox_inches=ext)

PURPLE, RED, DEEP, GREEN, LILAC, GOLD = \
    "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4", "#D4A017"
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3,
                     "axes.titlesize": 11, "figure.dpi": 110})


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---------- Fig S1: device-model validation (LLG vs behavioral sigmoid) ----------
def fig1():
    d = jload(TB / "llg_validate_summary.json")
    V = np.array(d["V"]); pl = np.array(d["psw_llg"]); pb = np.array(d["psw_beh"])
    ci = np.array(d["wilson95"])
    Vg, pg = [], []
    with open(TB / "golden_psw.csv") as f:
        for r in csv.DictReader(f):
            Vg.append(float(r["V"])); pg.append(float(r["psw"]))
    Vg, pg = np.array(Vg), np.array(pg)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.plot(Vg, pg, "-", color=PURPLE, lw=2.2, label="behavioral sigmoid (calibrated)")
    ax.errorbar(V, pl, yerr=ci, fmt="o", color=RED, ms=6, capsize=3, lw=1.4,
                label="macrospin LLG Monte-Carlo (200 trials)")
    ax.axvline(d["VTH"], color="0.4", ls="--", lw=1.2)
    ax.axhline(0.5, color="0.7", ls=":", lw=1.0)
    ax.text(d["VTH"] + 0.002, 0.06, r"$V_{th}=%.4f$ V" % d["VTH"], color="0.3", fontsize=9)
    ax.set_xlabel(r"write voltage $V$ (V)"); ax.set_ylabel(r"switching probability $P_{sw}$")
    ax.set_title(r"LLG vs behavioral $P_{sw}$ validation")
    ax.legend(fontsize=9, loc="upper left")
    fig.tight_layout(); fig.savefig(FIGDIR / "dual_model_consistency.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------- Fig S2: C1 slope-matched readout (offset vs V_T  +  Pareto boundary) ----------
def fig2():
    om = jload(HERO / "offset_mc_summary.json")
    pa = jload(HERO / "pareto_offset_cancellation_summary.json")
    sig = om["offset_sigma_mV"]; mu = om["offset_mean_mV"]; VT = om["VT_mV"]
    fig, ax = plt.subplots(1, 3, figsize=(16.6, 4.6))
    # (a) offset distribution vs the V_T decision window
    x = np.linspace(-3.2 * sig + mu, 3.2 * sig + mu, 400)
    g = np.exp(-0.5 * ((x - mu) / sig) ** 2) / (sig * np.sqrt(2 * np.pi))
    ax[0].fill_between(x, g, color=DEEP, alpha=0.55,
                       label=r"SA offset $\sigma$=%.2f mV=%.2f$\,V_T$ (N=120)" % (sig, sig / VT))
    ax[0].axvspan(-VT / 2, VT / 2, color=GOLD, alpha=0.30,
                  label=r"$V_T$ Bernoulli decision window (%.1f mV)" % VT)
    ax[0].axvline(0, color="0.5", ls=":", lw=1)
    ax[0].set_xlabel("input-referred offset (mV)"); ax[0].set_ylabel("density")
    ax[0].set_title(r"SA offset vs $V_T$ budget")
    ax[0].legend(fontsize=8.5)
    # (b) accuracy vs V_offset/V_T for each cancellation option at a representative readout
    cond = next(c for c in pa["conditions"] if c["V_in_V"] == 0.5 and "1024" in c["layer"])
    base = pa["baseline_pct"]
    names = [p["name"] for p in cond["points"]]
    offvt = [p["off_VT"] for p in cond["points"]]
    drop = [base - p["acc"] for p in cond["points"]]
    cost = [p["cost"] for p in cond["points"]]
    sc = ax[1].scatter(offvt, drop, s=[60 * c for c in cost], c=[PURPLE, DEEP, GREEN, RED],
                       edgecolor="black", zorder=3)
    for n, ox, dy in zip(names, offvt, drop):
        ax[1].annotate(n.replace("input-pair ", ""), (ox, dy), fontsize=8,
                       textcoords="offset points", xytext=(6, 4))
    ax[1].axhline(0.15, color="0.6", ls="--", lw=1, label="MNIST noise floor 0.15 pp")
    ax[1].set_xlabel(r"residual offset / $V_T$"); ax[1].set_ylabel("accuracy drop vs baseline (pp)")
    ax[1].set_title("Offset-cancellation Pareto")
    ax[1].legend(fontsize=8.5)
    cmp.plot_readout_sa(ax[2])
    fig.tight_layout()
    save_panels(fig, ax, "ch04_15")
    fig.savefig(OUT / "Chapter04_local_15.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------- Fig S3: write path -- IR-drop vs column height + driver end-to-end energy ----------
def fig3():
    ir = jload(WL / "ir_drop_summary.json")
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
    # (a) IR-drop % of 776 ohm vs N, per layer (from the N=256 sweep + realistic curve)
    Ns = [r["N"] for r in ir["realistic_met2_W1_pitch2"]]
    pct = [r["pct_of_776"] for r in ir["realistic_met2_W1_pitch2"]]
    ax[0].plot(Ns, pct, "o-", color=RED, lw=2, label="met2, W=1 um (round-trip)")
    ax[0].axhline(100, color="0.6", ls=":", lw=1)
    ax[0].axhspan(10, 20, color=GOLD, alpha=0.25, label="~10-20% budget band")
    ax[0].set_xscale("log", base=2); ax[0].set_yscale("log")
    ax[0].set_xlabel("column height N (cells)")
    ax[0].set_ylabel(r"parasitic R / 776 $\Omega$ (%)")
    ax[0].set_title("Write-line IR-drop vs column height")
    ax[0].legend(fontsize=9)
    # (b) sky130 CMOS write driver: delivered V and overhead vs pull-up width (measured)
    wp = [1, 2, 4, 6, 7, 8, 16, 32, 64]
    vflat = [0.188, 0.328, 0.589, 0.824, 0.927, 1.017, 1.421, 1.644, 1.758]
    ovh = [1088, 518, 228, 131, 105, 86, 33, 15, 8]
    ax2 = ax[1].twinx()
    l1, = ax[1].plot(wp, vflat, "s-", color=PURPLE, lw=2, label="delivered $V_{flat}$")
    ax[1].axhline(0.9, color="0.5", ls="--", lw=1)
    l2, = ax2.plot(wp, ovh, "o-", color=GREEN, lw=2, label="driver overhead %")
    ax[1].set_xscale("log", base=2)
    ax[1].set_xlabel(r"PMOS pull-up width $W_p$ (um)")
    ax[1].set_ylabel("delivered flat-top voltage (V)", color=PURPLE)
    ax2.set_ylabel("driver energy overhead (%)", color=GREEN)
    ax2.set_yscale("log")
    ax[1].set_title("Write-driver voltage delivery")
    ax[1].legend(handles=[l1, l2], fontsize=9, loc="center right")
    fig.tight_layout()
    save_panels(fig, ax, "ch04_16")
    fig.savefig(OUT / "Chapter04_local_16.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------- Fig S4: RC co-design -- iso-energy frontier + honest RC-vs-ESN ratio ----------
def fig4():
    iso = jload(TB / "rc_isoenergy_summary.json")
    rc = jload(TB / "rc_energy_recompute_summary.json")
    fig, ax = plt.subplots(1, 3, figsize=(16.6, 4.6))
    # (a) iso-energy frontier MC vs energy, colored by ADC bits
    fr = iso["frontier"]
    E = [p["E_fJ"] for p in fr]; MC = [p["MC"] for p in fr]; b = [p["b"] for p in fr]
    s = ax[0].scatter(E, MC, c=b, cmap="viridis", s=70, edgecolor="black", zorder=3)
    ax[0].plot(E, MC, "-", color="0.6", lw=1, zorder=1)
    ax[0].set_xscale("log")
    ax[0].set_xlabel("energy per step (fJ)"); ax[0].set_ylabel("memory capacity")
    ax[0].set_title("Reservoir MC vs energy (ADC bits)")
    fig.colorbar(s, ax=ax[0], label="ADC bits b")
    # (b) honest RC-vs-ESN ratio: baseline vs grounded ADC variants
    base = rc["baseline"]["ratio"]
    labels = ["readout\nw/o ADC", "per-node\n8-bit", "col-shared\n8-bit", "col-shared\n6-bit"]
    def gr(mmode, bb):
        return next(r["honest_ratio"] for r in rc["grounded"]
                   if r["M_mode"].startswith(mmode) and r["b"] == bb)
    vals = [base, gr("per", 8), gr("col", 8), gr("col", 6)]
    cols = [LILAC, RED, PURPLE, DEEP]
    ax[1].bar(labels, vals, color=cols, edgecolor="black")
    for i, v in enumerate(vals):
        ax[1].text(i, v + 0.6, "%.0f$\\times$" % v, ha="center", fontsize=10)
    ax[1].axhspan(30, 35, color=GOLD, alpha=0.25, label="30-35x with physical ADC")
    ax[1].set_ylabel(r"energy advantage vs digital ESN ($\times$)")
    ax[1].set_title("RC energy advantage vs digital ESN")
    ax[1].legend(fontsize=9)
    cmp.plot_sar(ax[2])
    fig.tight_layout()
    save_panels(fig, ax, "ch05_09")
    fig.savefig(OUT / "Chapter05_local_09.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------- Fig S5: forward design -- IR-aware per-row write pre-distortion ----------
def fig5():
    d = jload(HERO / "ir_aware_writedac_summary.json")
    N = d["N"]; Vt = d["V_target"]; Iw = d["I_write_mA"] * 1e-3
    rs = {"met1": 0.125, "met2": 0.125, "met3": 0.047}[d["layer"]]
    pitch, W = d["pitch_um"], d["W_um"]
    VTH, VT = 0.895783, 0.023414
    r = np.arange(0, N + 1)
    rpar = 2.0 * rs * (r * pitch / W)
    v_nopd = Vt - Iw * rpar
    psw = lambda v: 1.0 / (1.0 + np.exp(-(v - VTH) / VT))
    fig, ax = plt.subplots(1, 3, figsize=(16.6, 4.6))
    # (a) per-row write voltage: droop vs flattened, with the calibrated V_th crossing
    ax[0].plot(r, v_nopd, "-", color=RED, lw=2, label="no compensation (base-driven)")
    ax[0].axhline(Vt, color=PURPLE, lw=2, ls="--", label="IR-aware pre-distortion")
    ax[0].axhline(VTH, color=GREEN, lw=1.6, ls=":", label=r"calibrated $V_\mathrm{th}=%.3f$ V" % VTH)
    ax[0].fill_between(r, v_nopd, VTH, where=(v_nopd < VTH), color=RED, alpha=0.16)
    below = np.where(v_nopd < VTH)[0]
    if len(below):
        rc = int(below[0]); drop_mV = (Vt - v_nopd[-1]) * 1e3
        ax[0].axvline(rc, color="0.55", lw=0.9, ls=":")
        ax[0].annotate(f"remote cells drop\nbelow $V_{{\\mathrm{{th}}}}$ (row $\\gtrsim${rc});\n{drop_mV:.0f} mV end droop",
                       xy=(rc, VTH), xytext=(max(rc - 150, 5), VTH - 0.045), fontsize=8, color=RED)
    ax[0].set_xlabel("cell row in column"); ax[0].set_ylabel("write voltage at cell (V)")
    ax[0].set_title("Per-row write voltage")
    ax[0].legend(fontsize=8, loc="lower left")
    # (b) P_sw for three target operating points; pre-distortion holds each at target
    for pt, c in zip((0.5, 0.9, 0.99), (DEEP, RED, PURPLE)):
        Vtgt = VTH + VT * np.log(pt / (1 - pt))
        v = Vtgt - (Vtgt / 776.0) * rpar
        ax[1].plot(r, psw(v), "-", color=c, lw=1.9, label=r"$P_\mathrm{target}=%.2f$" % pt)
        ax[1].axhline(pt, color=c, lw=1.1, ls="--", alpha=0.7)
    ax[1].plot([], [], color="0.5", ls="--", label="IR-aware pre-distortion")
    ax[1].set_xlabel("cell row in column"); ax[1].set_ylabel(r"write probability $P_\mathrm{sw}$")
    ax[1].set_title(r"Pre-distortion holds $P_\mathrm{sw}$ on target")
    ax[1].legend(fontsize=7.5, loc="center left")
    cmp.plot_write_dac(ax[2])
    fig.tight_layout()
    save_panels(fig, ax, "ch04_17")
    fig.savefig(OUT / "Chapter04_local_17.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig1, fig2, fig3, fig4, fig5):
        f(); print("wrote", f.__name__)
    print("EDA analysis figures -> article/figs/Chapter04_local_{15,16,17,21}.png + Chapter05_local_09.png")
