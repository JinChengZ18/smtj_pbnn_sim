"""MNIST evaluation entry: load checkpoint, run evaluation in chosen mode."""

from __future__ import annotations

import torch

from ..nn.pbnn_linear import ForwardMode, DeviceLayerParams
from ..nn.losses import binary_cross_entropy_loss
from ..device.variation import VariationConfig
from ..data.mnist import get_mnist_loaders
from ..train.train_loop import evaluate
from ..utils.logging import log
from ._mnist_train import PBNN_MLP


def _device_params_from_cfg(dev_cfg: dict) -> DeviceLayerParams:
    op = dev_cfg.get("operating_point", {})
    nb = dev_cfg.get("neel_brown", {})
    res = dev_cfg.get("resistance", {})
    return DeviceLayerParams(
        V_th_nom=float(op.get("V_th_nom", 0.894)),
        V_T_nom=float(op.get("V_T_nom", 1.0 / 44.6)),
        R_P_nom=float(res.get("R_P_nom", 4.9e3)),
        TMR_nom=float(res.get("TMR_nom", 1.0)),
        R_SOT_nom=float(res.get("R_SOT", 776.0)),
        Delta_nom=float(nb.get("Delta_nom", 4.91)),
        V_c0_nom=float(nb.get("V_c0_nom", 0.857)),
        eta_c=float(dev_cfg.get("eta_c", 5.34)),
        tau_0=float(nb.get("tau_0", 1.0e-9)),
        t_p=float(op.get("t_p", 0.75e-9)),
    )


def _variation_from_cfg(var_cfg: dict | None) -> VariationConfig | None:
    if not var_cfg or not var_cfg.get("enabled", True):
        return None
    return VariationConfig(
        mode=str(var_cfg.get("mode", "delta")),
        cv_delta=float(var_cfg.get("cv_delta", 0.077)),
        sigma_V_th_rel=float(var_cfg.get("sigma_V_th_rel", 0.05)),
        sigma_V_T_rel=float(var_cfg.get("sigma_V_T_rel", 0.10)),
        sigma_RP_rel=float(var_cfg.get("sigma_RP_rel", 0.05)),
        sigma_TMR_rel=float(var_cfg.get("sigma_TMR_rel", 0.10)),
        seed=var_cfg.get("seed"),
    )


def run(cfg: dict, ckpt_path: str, mode: str, T: int) -> int:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    state = torch.load(ckpt_path, map_location=device)
    saved_cfg = state.get("config", cfg)
    dp = _device_params_from_cfg(saved_cfg.get("device", {}))
    vc = _variation_from_cfg(saved_cfg.get("variation", {}))

    model_cfg = saved_cfg.get("model", {})
    model = PBNN_MLP(
        hidden=int(model_cfg.get("hidden", 1024)),
        device_params=dp, variation_cfg=vc, T_full_stack=int(T),
    ).to(device)
    model.load_state_dict(state["model_state"], strict=True)

    data_cfg = cfg.get("data", {})
    _, test_loader = get_mnist_loaders(
        root=data_cfg.get("root", "./data/mnist"),
        batch_size=int(data_cfg.get("batch_size", 128)),
        num_workers=int(data_cfg.get("num_workers", 2)),
    )

    fm = ForwardMode(mode)
    loss, acc = evaluate(model, test_loader, binary_cross_entropy_loss, device,
                         mode=fm, T=T)
    log(f"mode={mode} T={T}  loss={loss:.4f}  acc={acc:.4f}")
    return 0
