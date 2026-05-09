"""Generic training loop and evaluation utility for PBNN models."""

from __future__ import annotations

from typing import Callable, Optional
import torch
from torch import Tensor
from torch.utils.data import DataLoader

from ..nn.pbnn_linear import ForwardMode
from ..utils.logging import log


def train_one_epoch(
    model: torch.nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: Callable[[Tensor, Tensor], Tensor],
    device: torch.device,
    *,
    mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
    grad_clip: Optional[float] = None,
) -> tuple[float, float]:
    """Train one epoch.

    Returns:
        ``(avg_loss, accuracy)`` over the epoch.
    """
    model.train()
    total_loss = 0.0
    n_correct = 0
    n_total = 0

    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)
        logits = _forward_with_mode(model, x, mode)
        loss = criterion(logits, y)
        loss.backward()
        if grad_clip is not None:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
        optimizer.step()

        total_loss += loss.item() * x.size(0)
        with torch.no_grad():
            pred = logits.argmax(dim=1)
            n_correct += int((pred == y).sum().item())
            n_total += int(y.numel())

    return total_loss / max(1, n_total), n_correct / max(1, n_total)


@torch.no_grad()
def evaluate(
    model: torch.nn.Module,
    loader: DataLoader,
    criterion: Callable[[Tensor, Tensor], Tensor],
    device: torch.device,
    *,
    mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
    T: Optional[int] = None,
) -> tuple[float, float]:
    """Evaluate the model on a held-out loader.

    For ``FULL_STACK`` mode, ``T`` overrides the per-layer default.
    """
    model.eval()
    total_loss = 0.0
    n_correct = 0
    n_total = 0

    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        logits = _forward_with_mode(model, x, mode, T=T)
        loss = criterion(logits, y)
        total_loss += loss.item() * x.size(0)
        pred = logits.argmax(dim=1)
        n_correct += int((pred == y).sum().item())
        n_total += int(y.numel())

    return total_loss / max(1, n_total), n_correct / max(1, n_total)


# -----------------------------------------------------------------------------#
# BN calibration for FULL_STACK evaluation                                      #
# -----------------------------------------------------------------------------#

@torch.no_grad()
def calibrate_bn(
    model: torch.nn.Module,
    loader: DataLoader,
    device: torch.device,
    *,
    mode: ForwardMode = ForwardMode.FULL_STACK,
    T: Optional[int] = None,
    num_batches: int = 50,
) -> None:
    """Recalibrate BatchNorm running stats for a different forward mode.

    When training uses HARDWARE_AWARE (deterministic CLT mean) but evaluation
    uses FULL_STACK (T-step Bernoulli sampling), the BN running statistics
    computed during training don't account for the sampling noise in the
    preactivation. This function runs a forward pass through ``num_batches``
    to update the running mean and variance so that they match the statistics
    of the target evaluation mode.

    The model is put into ``train()`` mode (so BN updates running stats),
    but all computation is done under ``torch.no_grad()``.
    """
    model.train()
    # Reset running stats so they are freshly estimated.
    for m in model.modules():
        if isinstance(m, (torch.nn.BatchNorm1d, torch.nn.BatchNorm2d)):
            m.running_mean.zero_()
            m.running_var.fill_(1.0)
            m.num_batches_tracked.zero_()

    for i, (x, _) in enumerate(loader):
        if i >= num_batches:
            break
        x = x.to(device, non_blocking=True)
        _forward_with_mode(model, x, mode, T=T)

    model.eval()
    log(f"BN calibrated for mode={mode.value} T={T} ({min(num_batches, len(loader))} batches)")


# -----------------------------------------------------------------------------#
# Helper: forward through a model that may have multiple PBNN layers, threading
# the forward `mode` and optional `T` through every layer that accepts them.    #
# -----------------------------------------------------------------------------#

def _forward_with_mode(model: torch.nn.Module, x: Tensor,
                       mode: ForwardMode, T: Optional[int] = None) -> Tensor:
    """Forward through a model whose modules may take a `mode=` kwarg.

    Plain ``nn.Module``s without that signature are called without the kwarg;
    PBNN modules receive the mode (and T) at every call. The model is
    expected to expose its own ``forward`` that accepts ``mode`` and ``T``
    and threads them downward, but a fallback is provided for simple
    sequential models.
    """
    if hasattr(model, "forward_with_mode"):
        return model.forward_with_mode(x, mode=mode, T=T)
    # Fallback: assume the model's own `forward` accepts (x, mode=, T=).
    try:
        return model(x, mode=mode, T=T)
    except TypeError:
        return model(x)
