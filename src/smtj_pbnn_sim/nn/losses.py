"""Loss functions and regularizers for PBNN training."""

from __future__ import annotations

import torch
from torch import Tensor


def binary_cross_entropy_loss(logits: Tensor, target: Tensor) -> Tensor:
    """Standard cross-entropy on the network logits.

    Despite the module name, this is plain ``F.cross_entropy``; the function
    exists to centralize the loss choice in case future variants of PBNN
    require a custom loss (for example, a temperature-scaled softmax for
    matched calibration with full-stack inference).
    """
    return torch.nn.functional.cross_entropy(logits, target)


def mutual_information_regularizer(theta: Tensor, beta: float = 1e-4) -> Tensor:
    """Encourage informative (non-saturated) Bernoulli weights.

    The Bernoulli entropy H(p) = -p log p - (1-p) log(1-p) is maximized at
    p = 1/2. Adding ``-beta * H(p)`` to the loss penalizes the network for
    pushing p toward 0 or 1, which keeps the stochastic regime active and
    prevents the CLT shortcut from collapsing to a deterministic linear
    layer in the limit. The default ``beta`` is small; tune as needed.
    """
    p = torch.sigmoid(theta).clamp(1e-6, 1.0 - 1e-6)
    H = -(p * torch.log(p) + (1.0 - p) * torch.log(1.0 - p))
    # We add -beta * H so that minimizing the loss maximizes H (entropy).
    return -beta * H.mean()


def binarization_regularizer(theta: Tensor, alpha: float = 1e-2) -> Tensor:
    """Push Bernoulli weights toward deterministic ±1.

    The Bernoulli variance ``p(1-p)`` is maximized at p=1/2 and zero at p=0
    or p=1. Adding ``alpha * mean(p(1-p))`` to the loss penalizes
    non-binary weights, encouraging the network to commit to deterministic
    +1 or -1 for each weight. This is critical for ensuring that the
    trained model performs well under ``FULL_STACK`` (T-step Bernoulli
    sampling) evaluation, where soft weights (p ≈ 0.5) produce random
    outputs.
    """
    p = torch.sigmoid(theta)
    return alpha * (p * (1.0 - p)).mean()
