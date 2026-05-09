"""Peripheral circuit models: DAC and counter.

These are intentionally simple finite-precision models. Their main role
in the simulator is to inject quantization noise into the forward path
during ``full_stack`` evaluation, and to feed realistic per-call
energy/latency numbers into the PPA layer.

Both classes work with NumPy arrays or Torch tensors; the rounding and
clamping operations are dispatched on the input type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np


def _is_torch(x: Any) -> bool:
    return type(x).__module__.startswith("torch")


def _clamp(x, lo, hi):
    if _is_torch(x):
        return x.clamp(lo, hi)
    return np.clip(x, lo, hi)


def _round(x):
    if _is_torch(x):
        import torch
        return torch.round(x)
    return np.round(x)


@dataclass
class DACModel:
    """Finite-precision DAC for the write-voltage path.

    Attributes:
        n_bits: DAC resolution. Typical 4-6 bits for sMTJ-PBNN.
        v_min: Lowest output voltage [V].
        v_max: Highest output voltage [V].
    """
    n_bits: int = 5
    v_min: float = 0.0
    v_max: float = 1.1

    def quantize(self, V):
        """Round ``V`` to the nearest DAC level (clamped to [v_min, v_max])."""
        levels = (1 << int(self.n_bits)) - 1
        if levels <= 0:
            return _clamp(V, self.v_min, self.v_max)
        scale = (self.v_max - self.v_min) / levels
        clamped = _clamp(V, self.v_min, self.v_max)
        idx = _round((clamped - self.v_min) / scale)
        return self.v_min + idx * scale


@dataclass
class CounterModel:
    """Finite-precision integer accumulator for T-step time-domain unfolding.

    Attributes:
        n_bits: Counter width. Must satisfy n_bits >= ceil(log2(T * N + 1))
            to avoid saturation; default 16 is sufficient for typical T*N
            up to about 65k.
    """
    n_bits: int = 16

    def saturate(self, x):
        """Clamp ``x`` to the signed counter range."""
        max_val = (1 << (self.n_bits - 1)) - 1
        min_val = -max_val - 1
        return _clamp(x, min_val, max_val)
