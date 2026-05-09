"""T-step time-domain unfolding utility."""

from __future__ import annotations

from typing import Callable
import torch
from torch import Tensor


def t_step_mean(fn: Callable[[], Tensor], T: int) -> Tensor:
    """Repeatedly call ``fn`` and return the running mean of its outputs.

    Each call to ``fn`` should return a fresh stochastic sample of identical
    shape. The result is

        (1 / T) * sum_{t=1}^T fn()

    which converges to the underlying expectation at a rate O(1 / sqrt(T))
    in standard deviation.

    Args:
        fn: Zero-argument callable returning a tensor.
        T: Number of samples (must be a positive integer).

    Returns:
        Tensor with the same shape as ``fn()``.

    Raises:
        ValueError: If ``T <= 0``.
    """
    if T <= 0:
        raise ValueError(f"T must be positive, got {T}")

    acc = fn()
    if T == 1:
        return acc
    acc = acc.clone()
    for _ in range(T - 1):
        acc = acc + fn()
    return acc / T
