"""Inference utilities: T-step ensemble prediction."""

from __future__ import annotations

from typing import Optional
import torch
from torch import Tensor

from ..nn.pbnn_linear import ForwardMode
from .train_loop import _forward_with_mode


@torch.no_grad()
def predict_with_T_step(
    model: torch.nn.Module,
    x: Tensor,
    T: int,
    *,
    mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
) -> Tensor:
    """Average the model's softmax probabilities across ``T`` independent forward passes.

    Each forward draws an independent set of binary weights (and Bernoulli
    samples in the relevant layers), so the average of the resulting
    probabilities gives a Bayesian-style ensemble prediction. This is the
    inference-time analogue of CLT-Gaussian sampling at training time.

    Args:
        model: The trained network.
        x: Input tensor.
        T: Number of forward passes.
        mode: Forward mode for each pass (default ``HARDWARE_AWARE``).

    Returns:
        Tensor of averaged class probabilities, shape (B, num_classes).
    """
    if T <= 0:
        raise ValueError(f"T must be positive, got {T}")
    model.eval()
    probs_sum: Optional[Tensor] = None
    for _ in range(T):
        logits = _forward_with_mode(model, x, mode)
        probs = torch.softmax(logits, dim=-1)
        probs_sum = probs if probs_sum is None else (probs_sum + probs)
    return probs_sum / T
