"""Deterministic binary neural network layer (standard BNN).

Following Courbariaux et al. (BinaryConnect / BinaryNet), this layer
maintains real-valued latent weights and binarizes them in the forward
pass via ``sign(W)`` with the straight-through estimator (STE) for
gradients.

No device modeling, no variation, no stochastic sampling -- this is the
digital BNN baseline for comparison against the hardware-aware PBNN.
"""

from __future__ import annotations

import math

import torch
from torch import Tensor
import torch.nn.functional as F

from .ste import sign_ste


class DeterministicBinaryLinear(torch.nn.Module):
    """Fully-connected layer with binary weights via sign(W_real) + STE.

    The ``weight`` parameter stores real-valued latent weights.  In the
    forward pass, weights are binarized to {-1, +1} via :func:`sign_ste`,
    which uses the straight-through estimator for gradient computation.

    This is the standard digital BNN layer used in Courbariaux et al.
    (BinaryConnect, 2015) and Hubara et al. (BinaryNet, 2016).

    Parameters
    ----------
    in_features : int
        Size of each input sample.
    out_features : int
        Size of each output sample.
    bias : bool
        If ``True``, adds a learnable bias to the output. Default: ``True``.
    """

    def __init__(
        self,
        in_features: int,
        out_features: int,
        *,
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = torch.nn.Parameter(torch.empty(out_features, in_features))
        if bias:
            self.bias = torch.nn.Parameter(torch.zeros(out_features))
        else:
            self.register_parameter("bias", None)

        # Kaiming uniform initialization scaled for binary weights.
        with torch.no_grad():
            bound = 1.0 / math.sqrt(in_features)
            self.weight.uniform_(-bound, bound)

    def forward(self, x: Tensor) -> Tensor:
        """Forward with binarized weights: ``F.linear(x, sign(W), bias)``."""
        w_bin = sign_ste(self.weight)
        return F.linear(x, w_bin, self.bias)

    def extra_repr(self) -> str:
        return (
            f"in_features={self.in_features}, "
            f"out_features={self.out_features}, "
            f"bias={self.bias is not None}"
        )
