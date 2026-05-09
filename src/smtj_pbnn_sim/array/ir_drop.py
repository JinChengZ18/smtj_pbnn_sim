"""IR-drop model (optional).

Wire-resistance-induced voltage droop on metal lines becomes meaningful at
sub-array sizes above ~512x512 in advanced nodes, or with low-resistance
MTJ stacks. For the default 256x256 / R_P ~ 5 kohm operating point used in
this thesis it can be neglected at the single-bit readout level.

This module is left as a documented stub. To enable IR-drop modeling,
implement a simple resistive-ladder per-row solver and call it from
:meth:`smtj_pbnn_sim.array.tile.Tile.mac` before the `linear` call.

Reference:
    Wan et al., "Scaling limits of memristor-based routers for
    asynchronous neuromorphic systems", arXiv:2307.08116, 2023.
"""

from __future__ import annotations


def estimate_ir_drop(rows: int, cols: int, r_wire_per_cell: float,
                     r_cell: float) -> float:
    """First-order estimate of worst-case IR drop along a row.

    Args:
        rows: Number of rows in the crossbar.
        cols: Number of columns.
        r_wire_per_cell: Metal resistance per cell pitch [ohm].
        r_cell: Equivalent cell resistance [ohm].

    Returns:
        Worst-case voltage-droop fraction in [0, 1).
    """
    # Sum of arithmetic series for a uniformly loaded line.
    r_line = r_wire_per_cell * cols
    return r_line / (r_line + r_cell)
