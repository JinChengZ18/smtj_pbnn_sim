"""Straight-through estimator (STE) for the sign(.) activation.

Forward:   y = sign(x)   (with sign(0) defined as +1)
Backward:  dy/dx = clip(1, -1)  on the unit interval, zero outside

Following Bengio, Léonard, and Courville (arXiv:1308.3432, 2013), the
backward pass of a hard binarization is replaced by an identity within a
clipped region. This is a standard component of binary neural networks and
is used here for both the activation binarization and (where appropriate)
the deterministic component of the weight binarization.
"""

from __future__ import annotations

import torch
from torch import Tensor


class _SignSTE(torch.autograd.Function):
    """Sign with clipped straight-through gradient."""

    @staticmethod
    def forward(ctx, x: Tensor) -> Tensor:  # type: ignore[override]
        ctx.save_for_backward(x)
        # sign(0) is set to +1 to keep the output strictly binary.
        return torch.where(x >= 0, torch.ones_like(x), -torch.ones_like(x))

    @staticmethod
    def backward(ctx, grad_output: Tensor) -> Tensor:  # type: ignore[override]
        (x,) = ctx.saved_tensors
        # Identity within |x| <= 1, zero outside.
        passthrough = (x.abs() <= 1.0).to(grad_output.dtype)
        return grad_output * passthrough


def sign_ste(x: Tensor) -> Tensor:
    """Functional wrapper for the STE sign."""
    return _SignSTE.apply(x)


class SignSTE(torch.nn.Module):
    """Module wrapper for the STE sign."""

    def forward(self, x: Tensor) -> Tensor:  # type: ignore[override]
        return sign_ste(x)
