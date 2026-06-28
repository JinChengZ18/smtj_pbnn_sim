#!/usr/bin/env python3
"""Plot the operating waveforms for the supplement (fig 11).

(a) Write path  -- ngspice transient (write_tran_tb.spice): 0.75 ns write pulse delivered across
    the 776 ohm SOT branch, with the calibrated compact-model switching probability P_sw(t).
(b) Read path   -- ngspice transient (sa_tran_tb.spice): StrongARM regenerative latch resolving a
    10 mV differential after the clock edge (outputs precharged high, then split to the rails).
(c) Reservoir read-out -- behavioural SAR charge-redistribution conversion of a sampled column
    voltage (binary search; the cap-DAC reconstruction converges to the input over b bit-trials).
Data come from real ngspice runs (a, b); (c) is the SAR algorithm on the same column node.
Run with Windows Python (matplotlib). Outputs article/figs/Supplement_local_11.{png,svg,pdf}.
"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent.parent / "article" / "figs"
BLACK, RED, GREY, BLUE = "#1a1a1a", "#c0392b", "#888888", "#2c5aa0"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.linewidth": 0.9,
                     "axes.edgecolor": "#333333", "xtick.direction": "out", "ytick.direction": "out"})


def load(name):
    d = np.loadtxt(HERE / name)
    return d  # columns: t,v0, t,v1, t,v2


def main():
    fig, ax = plt.subplots(1, 3, figsize=(13.2, 3.7))

    # ---- (a) write path ----
    w = load("write_tran.csv")
    t = w[:, 0] * 1e9
    drvin, wr, psw = w[:, 1], w[:, 3], w[:, 5]
    a = ax[0]
    a.plot(t, drvin, color=GREY, lw=1.4, ls="--", label="drive pulse")
    a.plot(t, wr, color=BLACK, lw=1.8, label="delivered  V$_{wr}$")
    a.set_xlabel("time (ns)"); a.set_ylabel("voltage (V)")
    a.set_ylim(-0.05, 1.0); a.set_xlim(0, t.max())
    a2 = a.twinx()
    a2.plot(t, psw, color=RED, lw=1.8, label="P$_{sw}$(t)")
    a2.set_ylabel("switching prob. P$_{sw}$", color=RED); a2.tick_params(axis="y", colors=RED)
    a2.set_ylim(-0.03, 1.03)
    a.set_title("(a) write pulse delivery + stochastic switching", fontsize=10.5)
    h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
    a.legend(h1 + h2, l1 + l2, fontsize=8, loc="center right", framealpha=0.9)

    # ---- (b) StrongARM regeneration ----
    s = load("sa_tran.csv")
    ts = s[:, 0] * 1e9
    clk, outp, outn = s[:, 1], s[:, 3], s[:, 5]
    b = ax[1]
    b.plot(ts, clk, color=GREY, lw=1.3, ls="--", label="clk")
    b.plot(ts, outp, color=RED, lw=1.9, label="out+")
    b.plot(ts, outn, color=BLUE, lw=1.9, label="out−")
    b.axvline(1.0, color="#bbbbbb", lw=0.8, zorder=0)
    b.set_xlabel("time (ns)"); b.set_ylabel("voltage (V)")
    b.set_xlim(0, ts.max()); b.set_ylim(-0.1, 1.95)
    b.set_title("(b) StrongARM regeneration (10 mV input)", fontsize=10.5)
    b.legend(fontsize=8, loc="center right", framealpha=0.9)

    # ---- (c) SAR conversion (behavioural binary search) ----
    nb, vfs = 8, 1.0
    vin = 0.638 * vfs
    dac, levels = 0.0, []
    for i in range(nb):
        wt = vfs / 2 ** (i + 1)
        if vin >= dac + wt:
            dac += wt
        levels.append(dac)
    c = ax[2]
    idx = np.arange(1, nb + 1)
    c.axhline(vin, color=RED, lw=1.5, ls="--", label="sampled V$_x$")
    c.step(np.concatenate([[0], idx]), np.concatenate([[0], levels]), where="post",
           color=BLACK, lw=1.9, label="cap-DAC")
    c.plot(idx, levels, "o", color=BLACK, ms=4)
    c.set_xlabel("SAR bit-trial (MSB → LSB)"); c.set_ylabel("DAC voltage (V)")
    c.set_xlim(0, nb); c.set_ylim(0, vfs)
    c.set_title("(c) column-shared SAR conversion (%d-bit)" % nb, fontsize=10.5)
    c.legend(fontsize=8, loc="lower right", framealpha=0.9)

    for x in ax:
        x.grid(True, color="#e8e8e8", lw=0.7)
        x.set_axisbelow(True)
    fig.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIGS / f"Supplement_local_11.{ext}", dpi=200, bbox_inches="tight")
    print("wrote Supplement_local_11.{png,svg,pdf}")
    print(f"  SAR: vin={vin:.3f} -> dac={levels[-1]:.3f} V (err {abs(vin-levels[-1])*1e3:.1f} mV)")


if __name__ == "__main__":
    main()
