"""Crossbar primitive: XNOR-popcount and bit-line current sum.

For binary-binary linear products with x in {-1, +1} and w in {-1, +1}, the
inner product reduces to

    sum_j w_j x_j  =  2 * popcount(w XNOR x) - N,

which is the standard XNOR-popcount kernel of binary neural network CIM
macros (e.g., Pham et al. STT-BNN). At the analog level the same operation
manifests as a bit-line current

    I_BL  ~  sum_j G_j(state) * V_read(x_j),

where G_j depends on the cell's magnetic state. Both views are exposed here:
:func:`xnor_popcount` for the algorithmic equivalent, :func:`bitline_current`
for the analog-level current sum used by the PPA layer.
"""

from __future__ import annotations

from typing import Optional
import torch
from torch import Tensor

from ..device.tmr import MTJResistance, conductance_from_state


def xnor_popcount(x: Tensor, w: Tensor) -> Tensor:
    """Binary inner product via standard linear (no analog modeling).

    Args:
        x: Input of shape (..., N), values in {-1, +1}.
        w: Weight of shape (M, N), values in {-1, +1}.

    Returns:
        Tensor of shape (..., M).
    """
    return torch.nn.functional.linear(x, w)


def bitline_current(x: Tensor, w: Tensor, mtj: MTJResistance) -> Tensor:
    """Analog bit-line current sum.

    Args:
        x: Input voltages, shape (..., N), nominally x_j * V_read with
            x_j in {-1, +1}.
        w: Cell states, shape (M, N), values in {-1, +1}.
        mtj: Resistance description.

    Returns:
        Bit-line current tensor of shape (..., M).
    """
    G = conductance_from_state(w, mtj)
    return torch.nn.functional.linear(x, G)
