"""06a -- Sweep T_full_stack vs. CIFAR-10 test accuracy for the PBNN-CNN.

Companion to experiment 06 (MNIST + MLP). After training a model with
``05a_cifar10_pbnn_cnn.py``, this script reloads the checkpoint and
evaluates the network at T = 1, 2, 4, ..., 64 in FULL_STACK mode. It
plots accuracy vs T and accuracy vs total per-inference energy (per the
28 nm PPA tech parameters of the simulator), demonstrating that the
time-domain unfolding trade-off carries over from MLPs on MNIST to a
deeper binary CNN on a substantially harder dataset.

Outputs:
  - runs/06a_cifar10_sweep_T_<ts>/results.csv
  - runs/06a_cifar10_sweep_T_<ts>/06a_cifar10_sweep_T.png
  - figures/06a_cifar10_sweep_T.png

Run from the repo root (after experiment 05a has produced
``runs/cifar10_pbnn_cnn/best.pt``):

    python experiments/06a_cifar10_sweep_T_vs_accuracy.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Helpers                                                                      #
# ---------------------------------------------------------------------------#

def _device_params_from_ckpt(cfg: dict):
    """Rebuild a DeviceLayerParams from the checkpoint config."""
    from smtj_pbnn_sim.nn.pbnn_linear import DeviceLayerParams
    dev = cfg.get("device", {})
    op = dev.get("operating_point", {})
    nb = dev.get("neel_brown", {})
    res = dev.get("resistance", {})
    return DeviceLayerParams(
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


def _make_pbnn_cnn(*, base_ch: int, hidden_fc: int, num_classes: int,
                    device_params, T_full_stack: int):
    """Recreate the PBNN-CNN topology used in experiment 05a."""
    import torch
    from torch import nn, Tensor
    from smtj_pbnn_sim.nn.pbnn_conv import PBNNConv2d
    from smtj_pbnn_sim.nn.pbnn_linear import PBNNLinear, ForwardMode
    from smtj_pbnn_sim.nn.batchnorm import BinaryBatchNorm1d, BinaryBatchNorm2d
    from smtj_pbnn_sim.nn.ste import sign_ste

    # variation_cfg=None to match exp 06: training used HARDWARE_AWARE
    # with sign(theta) (invariant to variation in the binary forward),
    # so FULL_STACK evaluation should use nominal device parameters to
    # avoid corrupting Bernoulli probabilities with the delta-mode
    # systematic offset (see exp 06 comment).
    kw_pb = dict(device_params=device_params, variation_cfg=None,
                  T_full_stack=T_full_stack, binarize_output=False)

    class PBNN_CNN(nn.Module):
        def __init__(self):
            super().__init__()
            c1, c2, c3 = base_ch, 2 * base_ch, 4 * base_ch
            self.conv1 = nn.Conv2d(3, c1, 3, padding=1, bias=False)  # FP first layer
            self.bn1   = BinaryBatchNorm2d(c1)
            self.conv2 = PBNNConv2d(c1, c1, 3, padding=1, **kw_pb)
            self.bn2   = BinaryBatchNorm2d(c1)
            self.conv3 = PBNNConv2d(c1, c2, 3, padding=1, **kw_pb)
            self.bn3   = BinaryBatchNorm2d(c2)
            self.conv4 = PBNNConv2d(c2, c2, 3, padding=1, **kw_pb)
            self.bn4   = BinaryBatchNorm2d(c2)
            self.conv5 = PBNNConv2d(c2, c3, 3, padding=1, **kw_pb)
            self.bn5   = BinaryBatchNorm2d(c3)
            self.conv6 = PBNNConv2d(c3, c3, 3, padding=1, **kw_pb)
            self.bn6   = BinaryBatchNorm2d(c3)
            self.pool  = nn.MaxPool2d(2)
            flat = c3 * 4 * 4
            self.fc1 = PBNNLinear(flat,    hidden_fc,   **kw_pb)
            self.bn7 = BinaryBatchNorm1d(hidden_fc)
            self.fc2 = PBNNLinear(hidden_fc, num_classes, **kw_pb)

        def forward_with_mode(self, x: Tensor, *, mode: ForwardMode,
                              T: int | None = None) -> Tensor:
            sample = False
            def cb(conv, bn, x_in):
                z = conv(x_in, mode=mode, T=T, sample=sample)
                return sign_ste(bn(z))
            h = sign_ste(self.bn1(self.conv1(x)))  # FP first block
            h = self.pool(cb(self.conv2, self.bn2, h))
            h = cb(self.conv3, self.bn3, h)
            h = self.pool(cb(self.conv4, self.bn4, h))
            h = cb(self.conv5, self.bn5, h)
            h = self.pool(cb(self.conv6, self.bn6, h))
            h = h.reshape(h.size(0), -1)
            h = self.fc1(h, mode=mode, T=T, sample=sample)
            h = sign_ste(self.bn7(h))
            return self.fc2(h, mode=mode, T=T, sample=sample)

        def forward(self, x: Tensor, *,
                    mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
                    T: int | None = None) -> Tensor:
            return self.forward_with_mode(x, mode=mode, T=T)

    return PBNN_CNN


# ---------------------------------------------------------------------------#
# Main                                                                         #
# ---------------------------------------------------------------------------#

def main() -> None:
    try:
        import torch
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("PyTorch + matplotlib required.")
        sys.exit(1)

    import csv
    import shutil
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.utils.logging import log
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.cifar import get_cifar10_loaders
    from smtj_pbnn_sim.train.train_loop import evaluate, calibrate_bn
    from smtj_pbnn_sim.ppa import default_28nm, layer_inference_energy

    ckpt_path = REPO / "runs" / "cifar10_pbnn_cnn" / "best.pt"
    if not ckpt_path.exists():
        print(f"Checkpoint not found at {ckpt_path}.")
        print("Run experiments/05a_cifar10_pbnn_cnn.py first.")
        sys.exit(1)

    run_dir = make_run_dir("06a_cifar10_sweep_T", base=REPO / "runs")
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    state = torch.load(ckpt_path, map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_ckpt(cfg)
    model_cfg = cfg.get("model", {})
    base_ch = int(model_cfg.get("base_ch", 64))
    hidden_fc = int(model_cfg.get("hidden_fc", 1024))
    num_classes = int(model_cfg.get("num_classes", 10))
    batch_size = int(cfg.get("data", {}).get("batch_size", 128))

    train_loader, test_loader = get_cifar10_loaders(
        root="./data/cifar10", batch_size=batch_size, num_workers=0,
        augment=False)  # eval-time: deterministic loader, no augmentation

    Ts = [1, 2, 4, 8, 16, 32, 64]
    accs, energies = [], []
    tech = default_28nm()

    # PPA estimate per inference: sum across all conv + FC layers. Each
    # PBNN op corresponds to one tile call at out_features outputs and
    # in_features inputs accumulated over T draws. We use the simulator's
    # ``layer_inference_energy`` with the per-layer effective MAC count
    # (out_features * in_features after im2col).
    H, W = 32, 32  # CIFAR-10 input spatial size
    c1, c2, c3 = base_ch, 2 * base_ch, 4 * base_ch
    layer_dims = [
        # (out_features, in_features, n_spatial_positions)
        (c1, 3 * 3 * 3,            H * W),               # conv1 32x32
        (c1, c1 * 3 * 3,           H * W),               # conv2 32x32 (pool after)
        (c2, c1 * 3 * 3,           (H // 2) * (W // 2)),  # conv3 16x16
        (c2, c2 * 3 * 3,           (H // 2) * (W // 2)),  # conv4 16x16 (pool)
        (c3, c2 * 3 * 3,           (H // 4) * (W // 4)),  # conv5 8x8
        (c3, c3 * 3 * 3,           (H // 4) * (W // 4)),  # conv6 8x8 (pool)
        (hidden_fc,   c3 * 4 * 4, 1),                     # fc1
        (num_classes, hidden_fc,  1),                     # fc2
    ]

    PBNN_CNN = _make_pbnn_cnn(
        base_ch=base_ch, hidden_fc=hidden_fc, num_classes=num_classes,
        device_params=dp, T_full_stack=Ts[0])

    for T in Ts:
        model = PBNN_CNN().to(dev)
        # Update T_full_stack on every PBNN layer (rebuild the module so
        # variation/state are sampled cleanly each pass).
        for m in model.modules():
            if hasattr(m, "T_full_stack"):
                m.T_full_stack = T
        model.load_state_dict(state["model_state"], strict=True)

        calibrate_bn(model, train_loader, dev,
                     mode=ForwardMode.FULL_STACK, T=T, num_batches=50)
        _, acc = evaluate(model, test_loader, binary_cross_entropy_loss, dev,
                           mode=ForwardMode.FULL_STACK, T=T)

        # Total per-inference energy: sum layer energies, scaled by
        # spatial positions (each conv tile is reused at every output
        # spatial location).
        e_total = 0.0
        for (out_f, in_f, n_spatial) in layer_dims:
            e_layer = layer_inference_energy(out_f, in_f, T, tech)
            e_total += e_layer * n_spatial

        accs.append(acc)
        energies.append(e_total)
        log(f"  T = {T:3d}   acc = {acc:.4f}   "
            f"E ~= {e_total*1e6:.3f} uJ")

    # ----- Save CSV -----
    csv_path = run_dir / "results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["T", "accuracy", "energy_uJ"])
        for t, a, e in zip(Ts, accs, energies):
            w.writerow([t, f"{a:.6f}", f"{e*1e6:.6f}"])
    print(f"Results saved: {csv_path}")

    # ----- Plot -----
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(Ts, accs, "o-", color="#5E3F8C", lw=2)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Number of stochastic samples per inference, T")
    axes[0].set_ylabel("Test accuracy")
    axes[0].set_title("CIFAR-10 PBNN-CNN: accuracy vs. T")
    axes[0].grid(alpha=0.3, which="both")

    axes[1].plot([e * 1e6 for e in energies], accs, "s-",
                 color="#A82038", lw=2)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Per-inference energy (uJ)")
    axes[1].set_ylabel("Test accuracy")
    axes[1].set_title("CIFAR-10 PBNN-CNN: accuracy vs. energy")
    axes[1].grid(alpha=0.3, which="both")

    fig.tight_layout()
    out = REPO / "figures" / "06a_cifar10_sweep_T.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    shutil.copy2(out, run_dir / "06a_cifar10_sweep_T.png")
    print(f"Figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
