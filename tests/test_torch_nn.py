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


# -----------------------------------------------------------------------------#
# Variation effect                                                              #
# -----------------------------------------------------------------------------#

def test_variation_changes_soft_p_in_full_stack():
    """D2D variation should shift the soft switching probability.

    With the nominal-calibration V_wr, per-cell variation in V_th and V_T
    causes ``p_soft != sigmoid(theta)`` in FULL_STACK mode. We verify by
    comparing FULL_STACK output (large T, effectively the mean) with and
    without variation.
    """
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    from smtj_pbnn_sim.device.variation import VariationConfig
    torch.manual_seed(42)
    dp = DeviceLayerParams()

    # Without variation
    layer_no_var = PBNNLinear(32, 16, bias=False, device_params=dp,
                              variation_cfg=None, binarize_output=False,
                              T_full_stack=512)
    x = torch.randn(4, 32)
    with torch.no_grad():
        layer_no_var.theta.copy_(torch.randn(16, 32) * 3.0)  # moderate magnitude
    z_no_var = layer_no_var(x, mode=ForwardMode.FULL_STACK, T=512)

    # With variation (large CV to make effect visible)
    vc = VariationConfig(mode="delta", cv_delta=0.30, seed=99)
    layer_var = PBNNLinear(32, 16, bias=False, device_params=dp,
                            variation_cfg=vc, binarize_output=False,
                            T_full_stack=512)
    with torch.no_grad():
        layer_var.theta.copy_(layer_no_var.theta)
    z_var = layer_var(x, mode=ForwardMode.FULL_STACK, T=512)

    # The outputs should differ because variation shifts per-cell p values.
    # With CV=30% and moderate theta, the effect is clearly measurable.
    diff = (z_no_var - z_var).abs().max().item()
    assert diff > 0.1, (
        f"Variation had negligible effect on FULL_STACK output "
        f"(max diff = {diff:.4f}); the variation model may not be working."
    )


def test_no_variation_hardware_aware_matches_software():
    """Without variation, HARDWARE_AWARE should produce the same output as SOFTWARE.

    Both use hard binary weights sign(theta), and without variation the
    device Sigmoid reduces to the standard sigmoid(theta).
    """
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    torch.manual_seed(7)
    dp = DeviceLayerParams()
    layer = PBNNLinear(64, 32, bias=False, device_params=dp,
                       variation_cfg=None, binarize_output=False)
    x = torch.randn(4, 64)
    z_sw = layer(x, mode=ForwardMode.SOFTWARE, sample=False)
    z_hw = layer(x, mode=ForwardMode.HARDWARE_AWARE, sample=False)
    assert torch.allclose(z_sw, z_hw, atol=1e-5), (
        f"SOFTWARE and HARDWARE_AWARE differ without variation: "
        f"max diff = {(z_sw - z_hw).abs().max().item()}"
    )


# -----------------------------------------------------------------------------#
# C2C noise and back-hopping                                                    #
# -----------------------------------------------------------------------------#

def test_c2c_noise_increases_full_stack_variance():
    """C2C noise should increase variance of FULL_STACK output across runs.

    We compare the same layer with sigma_c2c=0 (deterministic p per draw)
    vs. sigma_c2c = 2*V_T (noisy p per draw). The noisy version should
    have measurably higher inter-run variance.
    """
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    dp_quiet = DeviceLayerParams(sigma_c2c=0.0)
    dp_noisy = DeviceLayerParams(sigma_c2c=2.0 * DeviceLayerParams().V_T_nom)

    x = torch.randn(2, 32)

    def _run_many(dp, n_runs=20):
        results = []
        for seed in range(n_runs):
            torch.manual_seed(seed)
            layer = PBNNLinear(32, 8, bias=False, device_params=dp,
                                variation_cfg=None, binarize_output=False,
                                T_full_stack=16)
            # Set deterministic theta to isolate C2C effect
            with torch.no_grad():
                layer.theta.fill_(3.0)
            z = layer(x, mode=ForwardMode.FULL_STACK, T=16)
            results.append(z)
        return torch.stack(results)  # (n_runs, B, out)

    z_quiet = _run_many(dp_quiet)
    z_noisy = _run_many(dp_noisy)

    var_quiet = z_quiet.var(dim=0).mean().item()
    var_noisy = z_noisy.var(dim=0).mean().item()
    assert var_noisy > var_quiet * 1.5, (
        f"C2C noise did not increase variance enough: "
        f"quiet={var_quiet:.4f}, noisy={var_noisy:.4f}"
    )


def test_load_state_dict_redraws_variation():
    """Loading a checkpoint must not preserve stale variation buffers.

    Regression test: a model trained with delta-mode variation (V_th
    centered at 0.843 V) would produce stale V_th_field in the checkpoint.
    Loading into a model with variation_cfg=None should fill V_th_field
    with V_th_nom (0.894 V), not the checkpoint's 0.843 V.
    """
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    from smtj_pbnn_sim.device.variation import VariationConfig

    dp = DeviceLayerParams()

    # 1. Create a "source" layer WITH variation and forward once to populate buffers.
    vc = VariationConfig(mode="delta", cv_delta=0.30, seed=42)
    src = PBNNLinear(32, 8, bias=False, device_params=dp,
                     variation_cfg=vc, binarize_output=False)
    x = torch.randn(2, 32)
    _ = src(x, mode=ForwardMode.FULL_STACK, T=1)
    assert src._variation_drawn
    src_vth_mean = src.V_th_field.mean().item()

    # 2. Save and load into a "dst" layer WITHOUT variation.
    state = src.state_dict()
    dst = PBNNLinear(32, 8, bias=False, device_params=dp,
                     variation_cfg=None, binarize_output=False)
    dst.load_state_dict(state)

    # After loading, _variation_drawn should be False (forces re-draw).
    assert not dst._variation_drawn

    # 3. Forward on dst triggers _ensure_variation with variation_cfg=None,
    #    filling V_th_field with V_th_nom.
    _ = dst(x, mode=ForwardMode.FULL_STACK, T=1)
    assert dst._variation_drawn
    dst_vth_mean = dst.V_th_field.mean().item()

    # dst should use nominal V_th, not the source's varied V_th.
    assert abs(dst_vth_mean - dp.V_th_nom) < 1e-6, (
        f"After loading with variation_cfg=None, V_th_field should be "
        f"V_th_nom={dp.V_th_nom}, got {dst_vth_mean:.4f}"
    )


def test_p_max_clamps_full_stack_output():
    """Back-hopping ceiling should reduce FULL_STACK output magnitude.

    With p_max < 1, the switching probability is clamped, so the
    expected weight ``E[w] = 2*clip(p, 1-pm, pm) - 1`` has smaller
    magnitude than the ideal ``2p - 1``. For large positive theta
    (p -> 1), the ideal w = +1 but with p_max=0.6, w averages to
    2*0.6 - 1 = 0.2. This should measurably reduce the output.
    """
    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    dp_ideal = DeviceLayerParams(p_max=1.0)
    dp_clamp = DeviceLayerParams(p_max=0.6)

    torch.manual_seed(0)
    x = torch.ones(2, 32)  # all-ones input for easy analysis
    T = 256

    layer_ideal = PBNNLinear(32, 8, bias=False, device_params=dp_ideal,
                              variation_cfg=None, binarize_output=False,
                              T_full_stack=T)
    layer_clamp = PBNNLinear(32, 8, bias=False, device_params=dp_clamp,
                              variation_cfg=None, binarize_output=False,
                              T_full_stack=T)
    # Large positive theta => p ~= 1 => ideal w ~= +1
    with torch.no_grad():
        layer_ideal.theta.fill_(10.0)
        layer_clamp.theta.fill_(10.0)

    z_ideal = layer_ideal(x, mode=ForwardMode.FULL_STACK, T=T)
    z_clamp = layer_clamp(x, mode=ForwardMode.FULL_STACK, T=T)

    # Ideal output: ~32 (all weights = +1, input = ones(32))
    # Clamped output: ~32 * (2*0.6 - 1) = 32 * 0.2 = 6.4
    assert z_ideal.mean().item() > 25.0, (
        f"Ideal output too low: {z_ideal.mean().item():.2f}"
    )
    assert z_clamp.mean().item() < z_ideal.mean().item() * 0.5, (
        f"p_max clamp did not reduce output enough: "
        f"ideal={z_ideal.mean().item():.2f}, "
        f"clamped={z_clamp.mean().item():.2f}"
    )
