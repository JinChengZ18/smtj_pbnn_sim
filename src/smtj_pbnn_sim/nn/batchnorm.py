"""BatchNorm variants compatible with stochastic binary preactivations.

For PBNN we use standard PyTorch BatchNorm without modification at training
time, because the CLT-Gaussian preactivation already has well-defined
running statistics. We expose thin wrappers here to (a) document the
intended usage and (b) provide a single point at which BN momentum, eps,
and affine flags can be retuned for the binary regime if needed.

Following Shayer et al. (LAR-net), the affine scaling parameter is kept
learnable so that the network can absorb the scale change introduced by the
{-1, +1} -> sign(.) transition.
"""

from __future__ import annotations

import torch


class BinaryBatchNorm1d(torch.nn.BatchNorm1d):
    """BatchNorm1d with affine=True, momentum=0.1, eps=1e-5 (defaults)."""
    pass


class BinaryBatchNorm2d(torch.nn.BatchNorm2d):
    """BatchNorm2d with affine=True, momentum=0.1, eps=1e-5 (defaults)."""
    pass
