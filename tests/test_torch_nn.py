"""Tests requiring PyTorch.

These tests cover the network and sampling layers. They are automatically
skipped if PyTorch is not installed (e.g., in CI sandboxes without GPU/CPU
torch wheels).
"""

from __future__ import annotations

import math
import pytest

torch = pytest.importorskip("torch")
import numpy as np    # noqa: E402


# -----------------------------------------------------------------------------#
# STE                                                                           #
# -----------------------------------------------------------------------------#

def test_sign_ste_forward_is_pm1():
    from smtj_pbnn_sim.nn.ste import sign_ste
    x = torch.tensor([-1.5, -0.3, 0.0, 0.7, 2.0])
    y = sign_ste(x)
    assert torch.equal(y, torch.tensor([-1., -1., 1., 1., 1.]))


def test_sign_ste_backward_passthrough_inside_unit_interval():
    from smtj_pbnn_sim.nn.ste import sign_ste
    x = torch.tensor([-2.0, -0.5, 0.5, 2.0], requires_grad=True)
    y = sign_ste(x).sum()
    y.backward()
    # Inside |x|<=1 the gradient passes through (=1); outside it's zero.
    expected = torch.tensor([0.0, 1.0, 1.0, 0.0])
    assert torch.equal(x.grad, expected)


# -----------------------------------------------------------------------------#
# CLT                                                                           #
# -----------------------------------------------------------------------------#

def test_clt_mean_matches_explicit_sampling():
    """CLT-Gaussian mean should match the explicit Bernoulli mean for large N."""
    from smtj_pbnn_sim.nn.clt import bernoulli_pm1_clt_forward
    torch.manual_seed(0)
    M, N, B = 64, 256, 8
    p = torch.rand(M, N).clamp(0.05, 0.95)
    x = torch.randn(B, N)

    # CLT analytic mean
    z_mean_analytic = bernoulli_pm1_clt_forward(p, x, sample=False)

    # Empirical mean via T = 500 explicit Bernoulli samples
    T = 500
    acc = torch.zeros_like(z_mean_analytic)
    for _ in range(T):
        u = torch.rand(M, N)
        w = torch.where(p >= u, torch.ones_like(p), -torch.ones_like(p))
        acc += torch.nn.functional.linear(x, w)
    z_mean_empirical = acc / T

    # Normalize error by per-element standard error of the MC mean.
    # SE_ij = sqrt(sum_j 4*p*(1-p)*x_j^2 / T).  Under i.i.d. normal
    # assumption, the max z-score over B*M elements should be < 5 sigma
    # with overwhelming probability.
    var_w = 4.0 * p * (1.0 - p)
    se = (torch.nn.functional.linear(x * x, var_w) / T).sqrt().clamp_min(1e-8)
    z_scores = (z_mean_analytic - z_mean_empirical).abs() / se
    assert z_scores.max().item() < 5.0  # 5-sigma bound


def test_clt_sample_variance_decreases_with_N():
    """For x = ones, CLT preact std ~ sqrt(N * 4 p (1-p)) ~ O(sqrt N)."""
    from smtj_pbnn_sim.nn.clt import bernoulli_pm1_clt_forward
    torch.manual_seed(0)
    for N in (16, 64, 256, 1024):
        p = torch.full((1, N), 0.5)
        x = torch.ones(8, N)
        # Many CLT samples to estimate the std
        std_z = torch.stack([
            bernoulli_pm1_clt_forward(p, x, sample=True)
            for _ in range(64)
        ]).std()
        expected = math.sqrt(N)
        # Within a factor of 2 (CLT exact, finite empirical std)
        assert 0.5 * expected < std_z.item() < 2.0 * expected


# -----------------------------------------------------------------------------#
# PBNNLinear three-mode parity                                                  #
# -----------------------------------------------------------------------------#

def test_pbnn_linear_software_mode_no_variation_matches_sign():
    """In SOFTWARE mode, the layer forward uses hard binary weights sign(theta)."""
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    from smtj_pbnn_sim.nn.ste import sign_ste
    torch.manual_seed(0)
    layer = PBNNLinear(64, 32, bias=False, device_params=DeviceLayerParams(),
                       binarize_output=False)
    x = torch.randn(4, 64)
    z = layer(x, mode=ForwardMode.SOFTWARE, sample=False)
    # Forward uses hard binary weights via STE; with sample=False the
    # CLT mean is (2*p_hard - 1) @ x = sign(theta) @ x.
    w = sign_ste(layer.theta)
    z_ref = torch.nn.functional.linear(x, w)
    assert torch.allclose(z, z_ref, atol=1e-6)


def test_pbnn_linear_full_stack_converges_to_soft_mean():
    """FULL_STACK with large T should converge to the soft CLT mean.

    FULL_STACK samples Bernoulli(p_soft) where p_soft = sigmoid(theta).
    Its expected output is ``(2*p_soft - 1) @ x``. We scale theta to
    large magnitude so that p_soft is near 0/1 and convergence is fast.
    """
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    torch.manual_seed(0)
    layer = PBNNLinear(64, 16, bias=False, device_params=DeviceLayerParams(),
                       binarize_output=False)
    # Scale theta to make sigmoid near 0/1 (near-deterministic Bernoulli)
    with torch.no_grad():
        layer.theta.mul_(100.0)
    x = torch.randn(4, 64)
    # Soft mean: what FULL_STACK converges to
    p_soft = torch.sigmoid(layer.theta)
    z_soft = torch.nn.functional.linear(x, 2.0 * p_soft - 1.0)
    z_full = layer(x, mode=ForwardMode.FULL_STACK, T=2048)
    # With large |theta|, p_soft ≈ 0 or 1, so Bernoulli variance is
    # near zero. FULL_STACK should match the soft mean closely.
    assert (z_soft - z_full).abs().max().item() < 1.5


def test_pbnn_linear_grad_flows_through_theta():
    """Backprop through CLT path should give nonzero grad on theta."""
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    torch.manual_seed(0)
    layer = PBNNLinear(64, 16, device_params=DeviceLayerParams(),
                       binarize_output=False)
    x = torch.randn(4, 64)
    z = layer(x, mode=ForwardMode.HARDWARE_AWARE, sample=True)
    z.sum().backward()
    assert layer.theta.grad is not None
    assert layer.theta.grad.abs().sum() > 0
