"""Energy estimation for sMTJ-PBNN inference.

Composition per MAC (= one cell's contribution to one of the T samples
on one bit-line):

    e_mac = e_dac_step + e_smtj_write + e_smtj_read + e_count_inc

with ``e_smtj_write = V_wr^2 / R_SOT * t_p`` derived from Chapter 2.3.
For one full-stack inference call through one tile of size ``rows x cols``
with T samples,

    E_layer = e_mac * rows * cols * T   (+ off-chip access if any).
"""

from __future__ import annotations

from .tech_params import TechParams


def per_mac_energy(tech: TechParams) -> float:
    """Energy of one MAC at the time-domain unfolded level."""
    return (tech.e_dac_step
            + tech.e_smtj_write
            + tech.e_smtj_read
            + tech.e_count_inc)


def layer_inference_energy(rows: int, cols: int, T: int,
                           tech: TechParams,
                           extra_off_chip_bytes: int = 0) -> float:
    """Energy for one inference call through a single tile [J]."""
    e_macs = per_mac_energy(tech) * rows * cols * T
    e_dram = tech.e_dram_byte * extra_off_chip_bytes
    return e_macs + e_dram


def write_energy_breakdown(tech: TechParams) -> dict[str, float]:
    """Return a per-component breakdown for one MAC (for plotting)."""
    return {
        "DAC":        tech.e_dac_step,
        "sMTJ_write": tech.e_smtj_write,
        "sMTJ_read":  tech.e_smtj_read,
        "counter":    tech.e_count_inc,
    }
