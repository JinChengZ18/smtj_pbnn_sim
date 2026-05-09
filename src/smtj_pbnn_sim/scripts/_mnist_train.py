"""MNIST training implementation invoked by the CLI.

A small PBNN MLP is defined locally; for richer models add new files under
``smtj_pbnn_sim/scripts/`` or new dataset-specific modules.
"""

from __future__ import annotations

import time
from pathlib import Path
import torch
from torch import Tensor

from ..nn.pbnn_linear import PBNNLinear, ForwardMode, DeviceLayerParams
from ..nn.batchnorm import BinaryBatchNorm1d
from ..nn.losses import binary_cross_entropy_loss, mutual_information_regularizer, binarization_regularizer
from ..nn.ste import sign_ste
from ..device.variation import VariationConfig
from ..data.mnist import get_mnist_loaders
from ..train.train_loop import train_one_epoch, evaluate
from ..utils.seeding import set_global_seed
from ..utils.logging import log, MetricsLogger
from ..utils.io import dump_yaml


# ---------------------------------------------------------------------------#
# Model                                                                       #
# ---------------------------------------------------------------------------#

class PBNN_MLP(torch.nn.Module):
    """3-layer PBNN MLP for MNIST (input is real-valued, hidden is {-1, +1})."""

    def __init__(self, hidden: int = 1024, num_classes: int = 10,
                 device_params: DeviceLayerParams | None = None,
                 variation_cfg: VariationConfig | None = None,
                 T_full_stack: int = 16):
        super().__init__()
        kw = dict(device_params=device_params, variation_cfg=variation_cfg,
                  T_full_stack=T_full_stack)
        # binarize_output=False: binarization is handled externally by
        # BN → sign_ste, which ensures the STE gradient passes through
        # (BN normalizes preactivations to O(1), well within the STE
        # clipping region |z| ≤ 1).
        self.fc1 = PBNNLinear(28 * 28, hidden, binarize_output=False, **kw)
        self.bn1 = BinaryBatchNorm1d(hidden)
        self.fc2 = PBNNLinear(hidden, hidden, binarize_output=False, **kw)
        self.bn2 = BinaryBatchNorm1d(hidden)
        self.fc3 = PBNNLinear(hidden, num_classes, binarize_output=False, **kw)

    def forward_with_mode(self, x: Tensor, *, mode: ForwardMode,
                          T: int | None = None) -> Tensor:
        x = x.view(x.size(0), -1)
        # Use sample=False (deterministic CLT mean) during training.
        # The sign_ste already provides the essential binary stochastic
        # structure; CLT sampling noise adds O(sqrt(N)) variance to the
        # preactivations, which BN normalizes away in the forward pass
        # but attenuates gradients by 1/sigma_raw in the backward pass.
        # This matches the standard BNN training formulation (soft weights
        # 2p-1 ∈ [-1, 1] with STE binary activations).
        sample = False
        h = self.fc1(x, mode=mode, T=T, sample=sample)
        h = self.bn1(h)
        h = sign_ste(h)
        h = self.fc2(h, mode=mode, T=T, sample=sample)
        h = self.bn2(h)
        h = sign_ste(h)
        return self.fc3(h, mode=mode, T=T, sample=sample)

    def forward(self, x: Tensor, *, mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
                T: int | None = None) -> Tensor:
        return self.forward_with_mode(x, mode=mode, T=T)


# ---------------------------------------------------------------------------#
# Entry                                                                       #
# ---------------------------------------------------------------------------#

def run(cfg: dict, out_dir: Path) -> int:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(cfg, out_dir / "resolved.yaml")

    set_global_seed(int(cfg.get("seed", 0)))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ----- data -----
    data_cfg = cfg.get("data", {})
    train_loader, test_loader = get_mnist_loaders(
        root=data_cfg.get("root", "./data/mnist"),
        batch_size=int(data_cfg.get("batch_size", 128)),
        num_workers=int(data_cfg.get("num_workers", 2)),
    )

    # ----- model -----
    dev = cfg.get("device", {})
    op = dev.get("operating_point", {})
    nb = dev.get("neel_brown", {})
    res = dev.get("resistance", {})
    dp = DeviceLayerParams(
        V_th_nom=float(op.get("V_th_nom", 0.894)),
        V_T_nom=float(op.get("V_T_nom", 1.0 / 44.6)),
        R_P_nom=float(res.get("R_P_nom", 4.9e3)),
        TMR_nom=float(res.get("TMR_nom", 1.0)),
        R_SOT_nom=float(res.get("R_SOT", 776.0)),
        Delta_nom=float(nb.get("Delta_nom", 4.91)),
        V_c0_nom=float(nb.get("V_c0_nom", 0.857)),
        eta_c=float(dev.get("eta_c", 5.34)),
        tau_0=float(nb.get("tau_0", 1.0e-9)),
        t_p=float(op.get("t_p", 0.75e-9)),
    )
    var = cfg.get("variation", {})
    if var.get("enabled", True):
        vc = VariationConfig(
            mode=str(var.get("mode", "delta")),
            cv_delta=float(var.get("cv_delta", 0.077)),
            sigma_V_th_rel=float(var.get("sigma_V_th_rel", 0.05)),
            sigma_V_T_rel=float(var.get("sigma_V_T_rel", 0.10)),
            sigma_RP_rel=float(var.get("sigma_RP_rel", 0.05)),
            sigma_TMR_rel=float(var.get("sigma_TMR_rel", 0.10)),
            seed=var.get("seed"),
        )
    else:
        vc = None

    model_cfg = cfg.get("model", {})
    model = PBNN_MLP(
        hidden=int(model_cfg.get("hidden", 1024)),
        device_params=dp, variation_cfg=vc,
        T_full_stack=int(cfg.get("T_full_stack", 16)),
    ).to(device)

    # ----- optim -----
    opt_cfg = cfg.get("optim", {})
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(opt_cfg.get("lr", 1e-3)),
        weight_decay=float(opt_cfg.get("weight_decay", 0.0)),
    )

    n_epochs = int(cfg.get("epochs", 10))
    mi_beta = float(cfg.get("mi_beta", 0.0))
    bin_alpha = float(cfg.get("bin_alpha", 0.0))
    train_mode = ForwardMode(cfg.get("train_mode", "hardware_aware"))
    eval_mode = ForwardMode(cfg.get("eval_mode", "hardware_aware"))

    def criterion(logits: Tensor, target: Tensor) -> Tensor:
        loss = binary_cross_entropy_loss(logits, target)
        for m in model.modules():
            if isinstance(m, PBNNLinear):
                if mi_beta > 0.0:
                    loss = loss + mutual_information_regularizer(m.theta, mi_beta)
                if bin_alpha > 0.0:
                    loss = loss + binarization_regularizer(m.theta, bin_alpha)
        return loss

    logger = MetricsLogger(out_dir, n_epochs=n_epochs)
    best_acc = 0.0
    for epoch in range(n_epochs):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, optimizer, criterion, device, mode=train_mode)
        te_loss, te_acc = evaluate(
            model, test_loader, criterion, device, mode=eval_mode)
        elapsed = time.time() - t0
        logger.log_epoch(epoch + 1, tr_loss, tr_acc, te_loss, te_acc, elapsed)

        if te_acc > best_acc:
            best_acc = te_acc
            torch.save({"model_state": model.state_dict(),
                        "config": cfg,
                        "best_acc": best_acc},
                       out_dir / "best.pt")

    log(f"Best test accuracy: {best_acc:.4f}  (saved to {out_dir/'best.pt'})")

    # Post-training: scale theta to make sigmoid(theta) near 0/1 for
    # FULL_STACK evaluation. This doesn't change the HARDWARE_AWARE
    # forward (which uses sign(theta), invariant to positive scaling)
    # but makes the Bernoulli sampling nearly deterministic.
    best_state = torch.load(out_dir / "best.pt", map_location=device)
    model.load_state_dict(best_state["model_state"], strict=True)
    theta_scale = float(cfg.get("theta_scale", 100.0))
    with torch.no_grad():
        for m in model.modules():
            if isinstance(m, PBNNLinear):
                m.theta.mul_(theta_scale)
    # Verify accuracy is preserved after scaling
    _, te_acc_post = evaluate(model, test_loader, criterion, device, mode=eval_mode)
    log(f"After theta scaling (×{theta_scale}): test acc = {te_acc_post:.4f}")
    torch.save({"model_state": model.state_dict(),
                "config": cfg,
                "best_acc": best_acc,
                "theta_scale": theta_scale},
               out_dir / "best.pt")

    logger.dump_summary(best_acc=best_acc, theta_scale=theta_scale)
    logger.close()

    return 0
