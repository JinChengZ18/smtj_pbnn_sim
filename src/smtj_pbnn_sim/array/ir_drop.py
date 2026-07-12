"""Write-line IR-drop model (sky130-grounded, first-order droop).

Metal write-line resistance droops the delivered write voltage along a column: a cell at row ``r``
sees ``V_target - I_wr * R_par(r)``, where ``R_par(r)`` is the cumulative line resistance to that
row. At the thesis *read* operating point the popcount VOLTAGE droop across a cell is small (R_P in
the kohm range), but the popcount SLOPE compares wire resistance against the column Norton impedance
(R_P/N, ~100 ohm at N=64), not against R_P: the T3-5 replay co-simulation measured a 0.68x popcount
slope compression and 12.7 mV far-end drop on a met1/0.23 um/2 um-pitch bit-line at N=64
(eda/hero/replay_column_cosim.py) -- read-path negligibility therefore holds only with wider or
higher-metal bit-lines (met2/met3) or slope-aware calibration. The *write* line is significant at
tall columns. sky130 ``extresist`` extraction
(``eda/extraction/writeline/``; poly self-check 47.96 vs 48.2 ohm/sq) gives a round-trip (BL+SL)
write-line resistance of ~128 ohm at N=256 on met2 / 1 um width -- 16.5% of the 776 ohm SOT branch,
about 148 mV -- which pulls the remote write point below the calibrated 0.896 V threshold and shifts
the switching-probability Sigmoid, raising the remote write-error rate.

This module provides (i) the first-order droop estimate (a single write current ``I_wr=V_target/R_SOT``
flowing through the cumulative line resistance to each row -- a conservative droop that ignores the
distributed current re-injection of a full ladder solve), (ii) the per-row delivered-voltage and
switching-probability profile, and (iii) the IR-aware per-row write *pre-distortion* that restores the
target voltage at every row. It is exercised by ``experiments/20_write_ir_drop.py`` and can be applied
to a per-cell probability map via :func:`apply_write_ir`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:                      # keep the module importable without torch (see array/__init__)
    from torch import Tensor

# --- sky130-extracted write-line + calibrated device constants ------------------------------------#
R_WIRE_PER_CELL_MET2 = 0.5      # ohm per cell pitch, round-trip BL+SL, met2 @1 um (extresist: N=256 -> 128 ohm)
R_SOT = 776.0                   # SOT write-branch resistance [ohm] (Chapter 2.3)
V_TH = 0.8958                   # calibrated write threshold [V] (Chapter 2.3 / errata)
V_T = 0.02341                   # Bernoulli decision window [V]; Sigmoid slope beta_s = 1/V_T


def r_par(row: int, r_wire_per_cell: float = R_WIRE_PER_CELL_MET2) -> float:
    """Cumulative write-line parasitic resistance to ``row`` [ohm] (row 0 = driven end)."""
    return r_wire_per_cell * (row + 1)


def estimate_ir_drop(rows: int, r_wire_per_cell: float = R_WIRE_PER_CELL_MET2,
                     r_cell: float = R_SOT) -> float:
    """Worst-case (farthest row) IR-droop fraction of the delivered write voltage, in [0, 1)."""
    r_line = r_wire_per_cell * rows
    return r_line / (r_line + r_cell)


def psw(v: float) -> float:
    """Calibrated switching-probability Sigmoid at delivered voltage ``v`` [V]."""
    return 1.0 / (1.0 + math.exp(-(v - V_TH) / V_T))


def _i_wr(v_target: float) -> float:
    """First-order write current set by the target write voltage across the SOT branch [A]."""
    return v_target / R_SOT


def delivered_voltage(v_target: float, rows: int,
                      r_wire_per_cell: float = R_WIRE_PER_CELL_MET2,
                      predistort: bool = False) -> List[float]:
    """Per-row delivered write voltage.

    Without compensation each row droops by ``I_wr * R_par(r)``; with ``predistort`` the driver
    raises the head voltage by the same amount so every row receives ``v_target``.
    """
    i = _i_wr(v_target)
    if predistort:
        return [v_target for _ in range(rows)]
    return [v_target - i * r_par(r, r_wire_per_cell) for r in range(rows)]


def psw_profile(v_target: float, rows: int,
                r_wire_per_cell: float = R_WIRE_PER_CELL_MET2,
                predistort: bool = False) -> List[float]:
    """Per-row switching probability under (un)compensated write-line IR drop."""
    return [psw(v) for v in delivered_voltage(v_target, rows, r_wire_per_cell, predistort)]


def predistortion_codes(v_target: float, rows: int,
                        r_wire_per_cell: float = R_WIRE_PER_CELL_MET2) -> List[float]:
    """Per-row head-voltage boost ``I_wr * R_par(r)`` [V] that flattens the column to ``v_target``."""
    i = _i_wr(v_target)
    return [i * r_par(r, r_wire_per_cell) for r in range(rows)]


def apply_write_ir(p: Tensor, v_target: float,
                   r_wire_per_cell: float = R_WIRE_PER_CELL_MET2,
                   predistort: bool = False) -> Tensor:
    """Degrade a per-cell write-probability map ``p`` (shape (rows, cols)) by row-dependent IR drop.

    The nominal target probability ``p`` is realised at ``v_target``; rows farther from the driver
    receive less voltage and a lower switching probability (unless ``predistort`` restores it).
    Returns a new tensor; the input is unchanged. Default off in the accuracy path -- this models a
    tall-column write-fidelity effect; the read-path slope compression is a separate effect,
    measured in the T3-5 replay co-simulation (see module docstring).
    """
    import torch
    rows = p.shape[0]
    factors = psw_profile(v_target, rows, r_wire_per_cell, predistort)
    scale = torch.tensor(factors, dtype=p.dtype, device=p.device).clamp_(0.0, 1.0) / max(psw(v_target), 1e-9)
    return (p * scale.unsqueeze(1)).clamp_(0.0, 1.0)
