"""04 -- PPA breakdown at the Chapter 2.3 SOT operating point.

Plots the per-MAC energy decomposition (DAC, sMTJ-write, sMTJ-read,
counter) on a log axis, along with the area decomposition for one
256x256 tile. Uses the SOT write energy E = V_wr^2 / R_SOT * t_p from
Chapter 2.3 (~0.78 pJ at 0.9 V / 0.75 ns / 776 ohm).

Run from the repo root:

    python experiments/04_ppa_breakdown.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.ppa import default_28nm, per_mac_energy   # noqa: E402
from smtj_pbnn_sim.ppa.energy import write_energy_breakdown  # noqa: E402
from smtj_pbnn_sim.ppa import tile_area, layer_inference_energy, layer_inference_latency   # noqa: E402


def main() -> None:
    tech = default_28nm()

    # Energy breakdown
    bd = write_energy_breakdown(tech)
    total = per_mac_energy(tech)
    print(f"Per-MAC energy (V_wr = {tech.V_wr_nom} V, t_w = {tech.t_write*1e9:.2f} ns, "
          f"R_SOT = {tech.R_SOT:.0f} ohm):")
    for k, v in bd.items():
        print(f"  {k:11s}: {v*1e15:8.2f} fJ  ({v / total * 100:5.1f}%)")
    print(f"  {'total':11s}: {total*1e15:8.2f} fJ\n")

    # Per-tile breakdown for 256x256 with T = 16
    rows, cols, T = 256, 256, 16
    e_layer = layer_inference_energy(rows, cols, T, tech)
    t_layer = layer_inference_latency(rows, cols, T, tech)
    area = tile_area(rows, cols, tech)
    print(f"Per-inference at {rows}x{cols} tile, T = {T}:")
    print(f"  energy  = {e_layer*1e6:.3f} uJ")
    print(f"  latency = {t_layer*1e9:.2f} ns")
    print(f"  area    = {area:.1f} um^2")
    print()

    # Bar plot
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    components = list(bd.keys())
    fJ = [bd[k] * 1e15 for k in components]
    colors = ["#9580BD", "#A82038", "#5E3F8C", "#1A6B5A"]
    axes[0].bar(components, fJ, color=colors, edgecolor="black")
    for c, v in zip(components, fJ):
        axes[0].text(c, v * 1.05, f"{v:.1f} fJ", ha="center", fontsize=11)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Energy per MAC (fJ)")
    axes[0].set_title("Per-MAC energy breakdown (SOT operating point)")
    axes[0].grid(axis="y", alpha=0.3, which="both")

    # Area breakdown
    a_array = rows * cols * (tech.a_smtj_cell + tech.a_sot_track)
    a_dacs = rows * tech.a_dac
    a_counters = cols * tech.a_counter
    axes[1].bar(["array", "DACs", "counters"],
                [a_array, a_dacs, a_counters],
                color=["#5E3F8C", "#9580BD", "#C99FD4"],
                edgecolor="black")
    for i, v in enumerate([a_array, a_dacs, a_counters]):
        axes[1].text(i, v * 1.02, f"{v:.0f} $\\mu$m$^2$", ha="center", fontsize=11)
    axes[1].set_ylabel("Tile area ($\\mu$m$^2$)")
    axes[1].set_title(f"Tile area breakdown ({rows}x{cols})")
    axes[1].grid(axis="y", alpha=0.3)

    fig.tight_layout()
    out = REPO / "figures" / "04_ppa_breakdown.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"Figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
