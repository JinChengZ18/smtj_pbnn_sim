"""Predictive uncertainty quantification from T-step samples.

Given T independent class probability vectors p_t in R^C from one input,
two standard quantities are reported:

    * predictive entropy   H[E[p]]   -- total uncertainty
    * expected entropy     E[H[p]]   -- aleatoric component
    * mutual information   H[E[p]] - E[H[p]]  -- epistemic component

These follow Gal & Ghahramani's decomposition (2016) and are appropriate
for an ensemble interpretation of the stochastic forward pass.
"""

from __future__ import annotations

from typing import Optional
import torch
from torch import Tensor

from ..nn.pbnn_linear import ForwardMode
from .train_loop import _forward_with_mode


@torch.no_grad()
def predictive_uncertainty(
    model: torch.nn.Module,
    x: Tensor,
    T: int,
    *,
    mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
    eps: float = 1e-12,
) -> dict[str, Tensor]:
    """Compute predictive, expected, and mutual-information uncertainties.

    Returns:
        Dict with keys ``mean_probs``, ``predictive_entropy``,
        ``expected_entropy`` and ``mutual_information``, each of shape
        (B,) (entropies) or (B, C) (mean_probs).
    """
    if T <= 0:
        raise ValueError(f"T must be positive, got {T}")
    model.eval()
    probs_list = []
    for _ in range(T):
        logits = _forward_with_mode(model, x, mode)
        probs_list.append(torch.softmax(logits, dim=-1))
    probs = torch.stack(probs_list, dim=0)             # (T, B, C)
    mean_probs = probs.mean(dim=0)                     # (B, C)

    pred_H = -(mean_probs.clamp_min(eps) * mean_probs.clamp_min(eps).log()).sum(dim=-1)
    expt_H = -(probs.clamp_min(eps) * probs.clamp_min(eps).log()).sum(dim=-1).mean(dim=0)
    mi = pred_H - expt_H

    return {
        "mean_probs": mean_probs,
        "predictive_entropy": pred_H,
        "expected_entropy": expt_H,
        "mutual_information": mi,
    }
