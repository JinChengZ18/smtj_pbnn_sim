"""Bernoulli sampling that bridges the device Sigmoid to network-level binary samples.

Two entry points are exposed:

* :func:`bernoulli_from_voltage` — given a write-voltage tensor and per-cell
  ``(V_0, V_T)`` fields, returns a {-1, +1} sample using inverse-CDF sampling
  on the device Sigmoid. This is the path used by the array layer.

* :func:`bernoulli_from_theta` — given the latent parameter tensor ``θ``,
  returns a {-1, +1} sample with P(sample = +1) = sigmoid(θ). This is a
  device-independent shortcut used in `software` mode and in unit tests.

Both functions are non-differentiable; the autograd path for training goes
through :mod:`smtj_pbnn_sim.nn.clt` (CLT-Gaussian forward) instead.
"""

from __future__ import annotations

from typing import Optional
import torch
from torch import Tensor

from ..device.arrhenius import psw_sigmoid


def _bernoulli_pm1(p: Tensor, generator: Optional[torch.Generator] = None) -> Tensor:
    """Sample a {-1, +1} tensor with P(=+1) = p, elementwise.

    Inverse-CDF sampling: draw u ~ U(0, 1), output sign(p - u) under the
    convention that u = p maps to +1.
    """
    u = torch.rand(p.shape, dtype=p.dtype, device=p.device, generator=generator)
    return torch.where(p >= u, torch.ones_like(p), -torch.ones_like(p))


def bernoulli_from_voltage(
    V_wr: Tensor,
    V_0: Tensor,
    V_T: Tensor,
    *,
    generator: Optional[torch.Generator] = None,
) -> Tensor:
    """Draw {-1, +1} samples whose probability is set by the device Sigmoid.

    Args:
        V_wr: Per-cell write voltage [V]. Same shape as ``V_0`` and ``V_T``.
        V_0: Per-cell Sigmoid center [V].
        V_T: Per-cell Sigmoid slope  [V]. Must be positive.
        generator: Optional torch generator for reproducibility.

    Returns:
        Tensor of {-1, +1} of identical shape, detached from autograd.
    """
    with torch.no_grad():
        p = psw_sigmoid(V_wr, V_0, V_T)
        return _bernoulli_pm1(p, generator=generator)


def bernoulli_from_theta(
    theta: Tensor,
    *,
    generator: Optional[torch.Generator] = None,
) -> Tensor:
    """Draw {-1, +1} samples with P(=+1) = sigmoid(theta), no device model.

    This is the `software` shortcut; useful for sanity checks against the
    device-aware path and for reproducing published PBNN baselines.

    Args:
        theta: Latent parameter tensor.
        generator: Optional torch generator.

    Returns:
        Tensor of {-1, +1} of identical shape, detached from autograd.
    """
    with torch.no_grad():
        p = torch.sigmoid(theta)
        return _bernoulli_pm1(p, generator=generator)
