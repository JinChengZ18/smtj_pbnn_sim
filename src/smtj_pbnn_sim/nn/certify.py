"""Closed-form certification of PBNN accuracy under i.i.d. cell flips.

Theory
------
Each stored cell is an independent {-1, +1} Bernoulli draw with
P(+1) = q. An i.i.d. flip channel at rate ``p_flip`` (each cell's sign
inverted independently) maps the cell EXACTLY onto another Bernoulli:

    q' = (1 - 2 p_flip) q + p_flip                       (BSC contraction)

so the corrupted network is *equal in distribution* to the clean
architecture with every latent probability contracted toward 1/2: the
mean cell value scales by (1 - 2 p_flip) and the per-cell variance rises
to 1 - (1 - 2 p_flip)^2 mu^2. This holds jointly for all layers (cells
are independent), reducing corruption analysis to parameter contraction.
Positional (e.g. INT8) encodings admit no such reduction -- a flip's
effect depends on its bit position -- which is the structural root of
the empirical robustness gap (experiment 09).

Certification (last layer, conditional on binary features h)
------------------------------------------------------------
With h in {-1, +1}^N fixed and label y, the margin against class c is

    margin_yc = (2/T) S + (b_y - b_c),
    S = sum_{j, t} u_jt,   u = h_j (w_yjt - w_cjt) / 2 in {-1, 0, +1},

a sum of N T independent trinomial variables with, per input j
(r = q'_yj if h_j > 0 else 1 - q'_yj; s = q'_cj if h_j > 0 else 1 - q'_cj):

    P(u = +1) = a_j = r (1 - s),   P(u = -1) = b_j = (1 - r) s.

Exact moments follow in closed form; the misclassification tail
P(margin_yc <= 0) = P(S <= s0), s0 = -T (b_y - b_c) / 2, is bounded by
the minimum of (i) a Bernstein bound (increments centered, |u - Eu| <= 2)
and (ii) a Gaussian tail plus the non-i.i.d. Berry-Esseen remainder with
Shevtsova's constant 0.56 -- both non-asymptotic. The per-sample error
bound is the union over c != y; taking the expectation over h drawn from
the corrupted network itself (law of total expectation) yields a
rigorous end-to-end bound estimated by Monte Carlo over h draws.

The naive route -- treating the flip perturbation as zero-mean noise and
applying Hoeffding around the CLEAN margin -- is wrong: the perturbation
carries the systematic contraction term. The decomposition here keeps
the contracted mean exact and bounds only the genuine fluctuation.
"""
from __future__ import annotations

import math

import torch
from torch import Tensor

_BE_CONST = 0.56          # Berry-Esseen constant, independent non-iid summands
                          # (Shevtsova 2010, |P - Phi| <= 0.56 rho3 / sigma^3)


def contract_p(p: Tensor, p_flip: float) -> Tensor:
    """BSC contraction of Bernoulli(+1) probabilities under i.i.d. flips."""
    if not 0.0 <= p_flip <= 0.5:
        raise ValueError(f"p_flip must be in [0, 0.5], got {p_flip}")
    return (1.0 - 2.0 * p_flip) * p + p_flip


def margin_tail_bounds(q: Tensor, h: Tensor, y: Tensor, bias: Tensor | None,
                       T: int) -> Tensor:
    """Per-sample upper bounds on P(margin_yc <= 0) for every rival class.

    Args:
        q: contracted last-layer probabilities, shape (C, N).
        h: binary features in {-1, +1}, shape (B, N).
        y: labels, shape (B,).
        bias: last-layer bias, shape (C,) or None.
        T: stochastic samples per weight.

    Returns:
        err_pair: shape (B, C); entry (i, c) bounds P(margin_{y_i, c} <= 0),
        with the y-column set to 0.
    """
    B, N = h.shape
    C = q.shape[0]
    pos = h > 0                                          # (B, N)
    # r_ij = P(u-contribution of the TRUE class is +1-favourable)
    q_y = q[y]                                           # (B, N)
    r = torch.where(pos, q_y, 1.0 - q_y)                 # (B, N)
    # s_icj for every rival class: (B, C, N)
    q_all = q.unsqueeze(0).expand(B, C, N)
    s = torch.where(pos.unsqueeze(1), q_all, 1.0 - q_all)
    r_ = r.unsqueeze(1)                                  # (B, 1, N)
    a = r_ * (1.0 - s)                                   # P(u = +1)
    b = (1.0 - r_) * s                                   # P(u = -1)
    m1 = a - b                                           # E[u]
    var = a + b - m1 ** 2                                # Var[u]
    # E|u - m1|^3 exactly over the three outcomes {+1, -1, 0}
    rho = (torch.abs(1.0 - m1) ** 3 * a
           + torch.abs(1.0 + m1) ** 3 * b
           + torch.abs(m1) ** 3 * (1.0 - a - b))
    mu_S = T * m1.sum(-1)                                # (B, C)
    var_S = (T * var.sum(-1)).clamp_min(1e-12)
    rho_S = T * rho.sum(-1)
    sd_S = var_S.sqrt()

    if bias is not None:
        dbias = bias[y].unsqueeze(1) - bias.unsqueeze(0)  # (B, C)
        s0 = -T * dbias / 2.0
    else:
        s0 = torch.zeros_like(mu_S)

    t = mu_S - s0                                        # distance to failure
    # Bernstein: P(S - mu <= -t) <= exp(-t^2 / (2 var + 4 t / 3)), |u-Eu|<=2
    bern = torch.exp(-t.clamp_min(0.0) ** 2 / (2.0 * var_S + 4.0 * t.clamp_min(0.0) / 3.0))
    # Gaussian + Berry-Esseen remainder
    z = (s0 - mu_S) / sd_S
    gauss = 0.5 * (1.0 + torch.erf(z / math.sqrt(2.0)))
    be = (gauss + _BE_CONST * rho_S / sd_S ** 3).clamp(max=1.0)

    # both branches gated on t > 0: for t <= 0 the mean already sits on the
    # failure side and the degenerate zero-variance corner (Var(S) = 0 with
    # an exact tie) would otherwise let the Gaussian branch report 1/2 -- a
    # hole in the strict-bound claim (audit 2026-07-13)
    err = torch.where(t > 0, torch.minimum(bern, be), torch.ones_like(t))
    err.scatter_(1, y.unsqueeze(1), 0.0)                 # own class: no margin
    return err


def per_sample_error_bound(q: Tensor, h: Tensor, y: Tensor,
                           bias: Tensor | None, T: int) -> Tensor:
    """Union bound over rival classes: P(misclassify | h) <= sum_c err_c."""
    return margin_tail_bounds(q, h, y, bias, T).sum(1).clamp(max=1.0)
