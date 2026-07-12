"""Soundness tests for nn/certify.py against brute-force Monte Carlo.

The certification bounds must NEVER under-estimate the failure
probability (soundness); on comfortably-margined instances they must
also be informative (not vacuously 1).
"""
import math

import pytest
import torch

from smtj_pbnn_sim.nn.certify import (contract_p, margin_tail_bounds,
                                      per_sample_error_bound)


def test_contract_p_algebra():
    p = torch.tensor([0.0, 0.25, 0.5, 0.9, 1.0])
    out = contract_p(p, 0.1)
    expected = 0.8 * p + 0.1
    assert torch.allclose(out, expected)
    # p_flip = 0.5 erases all information
    assert torch.allclose(contract_p(p, 0.5), torch.full_like(p, 0.5))
    with pytest.raises(ValueError):
        contract_p(p, 0.6)


def test_flip_equals_contraction_in_distribution():
    """Sampling then flipping == sampling from the contracted probability."""
    torch.manual_seed(0)
    q, pf, n = 0.73, 0.12, 400_000
    w = (torch.rand(n) < q).float() * 2 - 1
    flip = (torch.rand(n) < pf).float()
    w_flipped = w * (1 - 2 * flip)
    q_emp = (w_flipped > 0).float().mean()
    q_contr = contract_p(torch.tensor(q), pf)
    assert abs(q_emp - q_contr) < 4 * math.sqrt(0.25 / n) + 1e-3


@pytest.mark.parametrize("t_samples", [2, 8])
def test_margin_bound_sound_vs_monte_carlo(t_samples):
    torch.manual_seed(1)
    C, N, B, MC = 3, 24, 4, 200_000
    q = torch.rand(C, N).clamp(0.05, 0.95)
    h = torch.where(torch.rand(B, N) > 0.5, 1.0, -1.0)
    y = torch.tensor([0, 1, 2, 0])
    bias = torch.randn(C) * 0.05

    bounds = margin_tail_bounds(q, h, y, bias, t_samples)     # (B, C)

    # brute-force margins
    w = (torch.rand(MC, C, N) < q).float() * 2 - 1            # one draw set
    for b in range(B):
        # redraw per (t, MC): sum over T independent draw sets
        s_mac = torch.zeros(MC, C)
        for _ in range(t_samples):
            w = (torch.rand(MC, C, N) < q).float() * 2 - 1
            s_mac += torch.einsum("mcn,n->mc", w, h[b])
        logits = s_mac / t_samples + bias
        m_y = logits[:, y[b]]
        for c in range(C):
            if c == int(y[b]):
                continue
            emp = float((m_y - logits[:, c] <= 0).float().mean())
            bd = float(bounds[b, c])
            mc_err = 4 * math.sqrt(max(emp * (1 - emp), 1e-9) / MC)
            assert emp <= bd + mc_err, (
                f"unsound: pair (y={int(y[b])}, c={c}) empirical {emp:.4f} "
                f"> bound {bd:.4f}")


def test_union_bound_sound_and_informative():
    torch.manual_seed(2)
    C, N, T = 5, 64, 8
    # comfortably separated: true class strongly favoured
    q = torch.full((C, N), 0.35)
    q[0] = 0.9
    h = torch.ones(2, N)
    y = torch.tensor([0, 0])
    eb = per_sample_error_bound(q, h, y, None, T)
    assert float(eb.max()) < 0.05          # informative, not vacuous
    # adversarial: rival identical to true class -> bound must be large
    q[1] = q[0]
    eb2 = per_sample_error_bound(q, h, y, None, T)
    assert float(eb2.min()) > 0.3          # ~coin-flip margin admitted
