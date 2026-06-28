"""Crossbar primitive: XNOR-popcount and bit-line current sum.

For binary-binary linear products with x in {-1, +1} and w in {-1, +1}, the
inner product reduces to

    sum_j w_j x_j  =  2 * popcount(w XNOR x) - N,

which is the standard XNOR-popcount kernel of binary neural network CIM
macros (e.g., Pham et al. STT-BNN). At the analog level the signed product is
realised *differentially* -- a cell and its complement drive two bit-lines and
the readout takes the difference, so the state-independent common-mode current
cancels and only the signed term survives:

    I_BL  =  sum_j [ G(+w_j) - G(-w_j) ] * V_read(x_j)  =  2 G_diff * sum_j x_j w_j.

Both views are exposed here: :func:`xnor_popcount` for the algorithmic
equivalent and :func:`bitline_current` for the differential analog current.

These are reference primitives illustrating the CIM mapping; the trained
network forward path uses the calibrated probabilistic kernels in
:mod:`smtj_pbnn_sim.nn`, not this module.
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
    """Differential analog bit-line current.

    Each cell ``w`` and its complement ``-w`` drive a positive and a negative
    bit-line; the readout takes the difference. The common-mode term
    ``G_mid * sum_j x_j`` (state-independent) cancels exactly, leaving the
    signed popcount current ``2 * G_diff * sum_j x_j w_j``.

    Args:
        x: Input voltages, shape (..., N), nominally x_j * V_read with
            x_j in {-1, +1}.
        w: Cell states, shape (M, N), values in {-1, +1}.
        mtj: Resistance description.

    Returns:
        Differential bit-line current tensor of shape (..., M).
    """
    G_pos = conductance_from_state(w, mtj)
    G_neg = conductance_from_state(-w, mtj)
    linear = torch.nn.functional.linear
    return linear(x, G_pos) - linear(x, G_neg)
