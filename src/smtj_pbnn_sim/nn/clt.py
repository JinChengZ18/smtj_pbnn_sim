"""Central-Limit-Theorem (CLT) Gaussian forward for stochastic binary weights.

For weights w_ij sampled independently from Bernoulli(p_ij) with values in
{-1, +1} (so E[w] = 2 p - 1, Var[w] = 4 p (1 - p)), the linear preactivation

    z_i = sum_j w_ij x_j

is a sum of N independent bounded random variables. By the Lyapunov CLT,
for sufficiently large N the distribution of z_i is approximately Gaussian
with

    mu_i     = sum_j (2 p_ij - 1) x_j
    sigma2_i = sum_j 4 p_ij (1 - p_ij) x_j^2.

This module computes (mu, sigma2) in closed form and reparameterizes the
Gaussian sample via z = mu + sigma * eps, eps ~ N(0, 1). The reparameterized
sample is differentiable in the latent parameters theta (with p = sigmoid(theta)),
which is what makes PBNN trainable end-to-end without per-sample REINFORCE.

The CLT shortcut replaces an explicit T-step Monte Carlo estimate during
training. At inference time, the discrepancy between the analytical Gaussian
and the empirical Bernoulli sum can be quantified by switching to
``full_stack`` mode in :class:`PBNNLinear`.
"""

from __future__ import annotations

import torch
from torch import Tensor


def bernoulli_pm1_clt_forward(
    p: Tensor,
    x: Tensor,
    *,
    sample: bool = True,
    eps_min: float = 1e-12,
) -> Tensor:
    """CLT-Gaussian linear forward for {-1, +1} Bernoulli weights.

    Args:
        p: Per-weight probability of +1, shape (M, N), in (0, 1).
        x: Input activations, shape (B, N).
        sample: If True, draw a Gaussian reparameterized sample. If False,
            return the mean (deterministic forward), useful for diagnostics.
        eps_min: Lower clamp on sigma^2 for numerical safety.

    Returns:
        Preactivation tensor of shape (B, M).
    """
    if p.dim() != 2:
        raise ValueError(f"p must be 2-D (M, N), got shape {tuple(p.shape)}")
    if x.dim() != 2:
        raise ValueError(f"x must be 2-D (B, N), got shape {tuple(x.shape)}")

    # mu:    (M, N) @ (N, B) -> (M, B), then transpose to (B, M)
    mean_w = 2.0 * p - 1.0                      # (M, N)
    var_w = 4.0 * p * (1.0 - p)                 # (M, N)

    mu = torch.nn.functional.linear(x, mean_w)  # (B, M)
    if not sample:
        return mu

    sigma2 = torch.nn.functional.linear(x * x, var_w).clamp_min(eps_min)
    sigma = sigma2.sqrt()
    eps = torch.randn_like(mu)
    return mu + sigma * eps


class BernoulliPm1CltLinear(torch.nn.Module):
    """Standalone CLT-Gaussian linear module (no device modeling).

    Convenient for unit tests and for reproducing the published PBNN
    baseline in `software` mode without going through the device + array
    layers.
    """

    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.theta = torch.nn.Parameter(torch.zeros(out_features, in_features))
        # Standard initialization scaled to keep the preactivation magnitude
        # comparable to a deterministic binary linear layer.
        with torch.no_grad():
            self.theta.normal_(mean=0.0, std=1.0 / max(1, in_features) ** 0.5)

    def forward(self, x: Tensor, *, sample: bool = True) -> Tensor:  # type: ignore[override]
        p = torch.sigmoid(self.theta)
        return bernoulli_pm1_clt_forward(p, x, sample=sample)
