"""Subarray tile: container for one M x N crossbar with its peripherals.

A :class:`Tile` represents one physical sub-array (typical 256x256 or
512x512). It owns the DAC, the counter and the MTJ resistance description,
and exposes a single ``mac`` method that performs one T-step XNOR-popcount
evaluation. The PBNN network does not call this directly during training
(the CLT shortcut bypasses it); it is invoked by ``full_stack`` evaluation
and by the PPA energy/latency estimators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import torch
from torch import Tensor

from ..device.tmr import MTJResistance
from .periphery import DACModel, CounterModel
from ..sampling.bernoulli_smtj import _bernoulli_pm1


@dataclass
class TileConfig:
    rows: int = 256
    cols: int = 256
    dac: DACModel = field(default_factory=DACModel)
    counter: CounterModel = field(default_factory=CounterModel)
    mtj: MTJResistance = field(default_factory=MTJResistance)


class Tile:
    """Physical sub-array tile with finite-precision peripherals."""

    def __init__(self, cfg: Optional[TileConfig] = None):
        self.cfg = cfg or TileConfig()

    def mac(self, x: Tensor, p: Tensor, T: int) -> Tensor:
        """T-step empirical mean of XNOR-popcount.

        Args:
            x: Input of shape (B, N), values in {-1, +1}.
            p: Per-cell probability, shape (M, N), in (0, 1).
            T: Number of independent draws.

        Returns:
            Mean preactivation tensor of shape (B, M).
        """
        if T <= 0:
            raise ValueError(f"T must be positive, got {T}")
        with torch.no_grad():
            acc: Optional[Tensor] = None
            for _ in range(T):
                w = _bernoulli_pm1(p)
                z_t = torch.nn.functional.linear(x, w)
                z_t = self.cfg.counter.saturate(z_t)
                acc = z_t if acc is None else (acc + z_t)
            return (acc / T) if acc is not None else torch.zeros(0)
