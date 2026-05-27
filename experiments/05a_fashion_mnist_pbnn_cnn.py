"""05a -- Fashion-MNIST PBNN-CNN training, with BNN and FP-CNN baselines.

Extends experiment 05 (MNIST + 3-layer MLP) to a substantially harder
classification task on the same 28x28 grayscale pipeline: Fashion-MNIST
(clothing categories) with a binary-CNN backbone.

The PBNN-CNN uses :class:`PBNNConv2d` (stochastic binary 2-D convolution
via Unfold -> CLT-linear -> reshape) for every convolutional layer, with
:class:`PBNNLinear` for the trailing fully-connected layers. Device
parameters and PDK-baseline variation match Chapter 2.3. The matched
baselines are:

  - BNN-CNN  : deterministic sign-STE conv/linear (digital BinaryNet,
               i.e. the special case of PBNN at single-point sampling
               with no sMTJ stochasticity).
  - FP-CNN   : nn.Conv2d / nn.Linear with ReLU activation (FP32 ideal).
  - INT8 QAT : symmetric weight quantization with straight-through
               estimator (typical digital CIM operating point).

All four share an identical topology
(1-64-64-128-128 conv with two maxpools + 1024 FC + 10 logits),
optimiser (Adam, lr=1e-3), batch (128) and epoch budget (default 20).

Outputs:
  - runs/05a_fashion_mnist_pbnn_cnn_<ts>/{best.pt, metrics.csv, summary.json}
                                              (PBNN)
  - runs/05a_fashion_mnist_pbnn_cnn_<ts>/bnn_metrics.csv
  - runs/05a_fashion_mnist_pbnn_cnn_<ts>/fp_*_metrics.csv
  - figures/05a_fashion_mnist_training_curves.png   2-panel: accuracy +
                                              loss vs epoch, all models
  - runs/fashion_mnist_pbnn_cnn/best.pt          stable copy used by 06a

Run from the repo root:

    python experiments/05a_fashion_mnist_pbnn_cnn.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Hyper-parameters / defaults                                                  #
# ---------------------------------------------------------------------------#

EPOCHS = 20            # matches experiment 05's MNIST budget
BATCH = 128
LR = 1e-3
BASE_CH = 64           # conv-block base channel count
HIDDEN_FC = 1024       # FC hidden width
NUM_CLASSES = 10
T_FULL_STACK = 8       # T for FULL_STACK at training/eval time


# ---------------------------------------------------------------------------#
# Model definitions (import-gated by torch)                                   #
# ---------------------------------------------------------------------------#

def _make_models(*, device_params, variation_cfg, T_full_stack: int,
                  base_ch: int = BASE_CH, hidden_fc: int = HIDDEN_FC,
                  num_classes: int = NUM_CLASSES):
    """Define PBNN/BNN/FP CNN model classes (import-gated by torch).

    All three share a 4-conv + 2-FC topology so that parameter counts and
    depths are matched and the per-epoch curves are directly comparable.
    Input: 1 channel, 28x28; output: num_classes logits.
    """
    import torch
    from torch import nn, Tensor

    from smtj_pbnn_sim.nn.pbnn_conv import PBNNConv2d
    from smtj_pbnn_sim.nn.pbnn_linear import PBNNLinear, ForwardMode
    from smtj_pbnn_sim.nn.deterministic_bnn import DeterministicBinaryLinear
    from smtj_pbnn_sim.nn.batchnorm import BinaryBatchNorm1d, BinaryBatchNorm2d
    from smtj_pbnn_sim.nn.ste import sign_ste

    kw_pb = dict(device_params=device_params, variation_cfg=variation_cfg,
                  T_full_stack=T_full_stack, binarize_output=False)

    # ----------------------------------------------------------------- PBNN
    class PBNN_CNN(nn.Module):
        """sMTJ-PBNN binary CNN for Fashion-MNIST.

        Four conv blocks at two resolutions, then two FC layers. All
        weights are PBNN (sign of latent theta with CLT-Gaussian forward
        in HARDWARE_AWARE mode, or T-step Bernoulli averaging in
        FULL_STACK mode). Activations are sign-STE.
        """

        def __init__(self):
            super().__init__()
            c1, c2 = base_ch, 2 * base_ch
            self.conv1 = PBNNConv2d(1,  c1, 3, padding=1, **kw_pb)
            self.bn1   = BinaryBatchNorm2d(c1)
            self.conv2 = PBNNConv2d(c1, c1, 3, padding=1, **kw_pb)
            self.bn2   = BinaryBatchNorm2d(c1)
            self.conv3 = PBNNConv2d(c1, c2, 3, padding=1, **kw_pb)
            self.bn3   = BinaryBatchNorm2d(c2)
            self.conv4 = PBNNConv2d(c2, c2, 3, padding=1, **kw_pb)
            self.bn4   = BinaryBatchNorm2d(c2)
            self.pool  = nn.MaxPool2d(2)
            # After 2 pools 28 -> 14 -> 7
            flat = c2 * 7 * 7
            self.fc1 = PBNNLinear(flat,    hidden_fc,   **kw_pb)
            self.bn5 = BinaryBatchNorm1d(hidden_fc)
            self.fc2 = PBNNLinear(hidden_fc, num_classes, **kw_pb)

        def forward_with_mode(self, x: Tensor, *, mode: ForwardMode,
                              T: int | None = None) -> Tensor:
            sample = False  # match exp 05 / _mnist_train.py rationale
            def cb(conv, bn, x_in):
                z = conv(x_in, mode=mode, T=T, sample=sample)
                return sign_ste(bn(z))
            h = cb(self.conv1, self.bn1, x)
            h = self.pool(cb(self.conv2, self.bn2, h))
            h = cb(self.conv3, self.bn3, h)
            h = self.pool(cb(self.conv4, self.bn4, h))
            h = h.reshape(h.size(0), -1)
            h = self.fc1(h, mode=mode, T=T, sample=sample)
            h = sign_ste(self.bn5(h))
            return self.fc2(h, mode=mode, T=T, sample=sample)

        def forward(self, x: Tensor, *,
                    mode: ForwardMode = ForwardMode.HARDWARE_AWARE,
                    T: int | None = None) -> Tensor:
            return self.forward_with_mode(x, mode=mode, T=T)

    # ----------------------------------------------------------------- BNN
    class _BinConv2d(nn.Conv2d):
        """nn.Conv2d with binary weights via sign_ste (digital BNN)."""

        def forward(self, x):
            w_bin = sign_ste(self.weight)
            return nn.functional.conv2d(
                x, w_bin, self.bias, self.stride, self.padding,
                self.dilation, self.groups)

    class BNN_CNN(nn.Module):
        """Matched-topology digital BNN baseline (BinaryNet)."""

        def __init__(self):
            super().__init__()
            c1, c2 = base_ch, 2 * base_ch
            self.conv1 = _BinConv2d(1,  c1, 3, padding=1)
            self.bn1   = BinaryBatchNorm2d(c1)
            self.conv2 = _BinConv2d(c1, c1, 3, padding=1)
            self.bn2   = BinaryBatchNorm2d(c1)
            self.conv3 = _BinConv2d(c1, c2, 3, padding=1)
            self.bn3   = BinaryBatchNorm2d(c2)
            self.conv4 = _BinConv2d(c2, c2, 3, padding=1)
            self.bn4   = BinaryBatchNorm2d(c2)
            self.pool  = nn.MaxPool2d(2)
            flat = c2 * 7 * 7
            self.fc1 = DeterministicBinaryLinear(flat, hidden_fc)
            self.bn5 = BinaryBatchNorm1d(hidden_fc)
            self.fc2 = DeterministicBinaryLinear(hidden_fc, num_classes)

        def forward(self, x):
            def cb(conv, bn, x_in):
                return sign_ste(bn(conv(x_in)))
            h = cb(self.conv1, self.bn1, x)
            h = self.pool(cb(self.conv2, self.bn2, h))
            h = cb(self.conv3, self.bn3, h)
            h = self.pool(cb(self.conv4, self.bn4, h))
            h = h.reshape(h.size(0), -1)
            h = sign_ste(self.bn5(self.fc1(h)))
            return self.fc2(h)

    # ----------------------------------------------------------------- FP / INT-QAT
    class _QuantizeSTE(torch.autograd.Function):
        @staticmethod
        def forward(ctx, w, bits):
            if bits >= 32:
                return w
            n_levels = 2 ** (bits - 1) - 1
            n_levels = max(n_levels, 1)
            scale = w.abs().max().clamp_min(1e-8) / n_levels
            return (w / scale).round().clamp(-n_levels, n_levels) * scale

        @staticmethod
        def backward(ctx, g):
            return g, None

    class _QConv2d(nn.Conv2d):
        def __init__(self, *args, bits=32, **kwargs):
            super().__init__(*args, **kwargs)
            self.bits = bits

        def forward(self, x):
            w_q = _QuantizeSTE.apply(self.weight, self.bits)
            return nn.functional.conv2d(
                x, w_q, self.bias, self.stride, self.padding,
                self.dilation, self.groups)

    class _QLinear(nn.Linear):
        def __init__(self, *args, bits=32, **kwargs):
            super().__init__(*args, **kwargs)
            self.bits = bits

        def forward(self, x):
            w_q = _QuantizeSTE.apply(self.weight, self.bits)
            return nn.functional.linear(x, w_q, self.bias)

    class FP_CNN(nn.Module):
        """Matched-topology FP/INT-QAT baseline (Conv-BN-ReLU)."""

        def __init__(self, bits: int = 32):
            super().__init__()
            c1, c2 = base_ch, 2 * base_ch
            self.conv1 = _QConv2d(1,  c1, 3, padding=1, bits=bits)
            self.bn1   = nn.BatchNorm2d(c1)
            self.conv2 = _QConv2d(c1, c1, 3, padding=1, bits=bits)
            self.bn2   = nn.BatchNorm2d(c1)
            self.conv3 = _QConv2d(c1, c2, 3, padding=1, bits=bits)
            self.bn3   = nn.BatchNorm2d(c2)
            self.conv4 = _QConv2d(c2, c2, 3, padding=1, bits=bits)
            self.bn4   = nn.BatchNorm2d(c2)
            self.pool  = nn.MaxPool2d(2)
            flat = c2 * 7 * 7
            self.fc1 = _QLinear(flat, hidden_fc, bits=bits)
            self.bn5 = nn.BatchNorm1d(hidden_fc)
            self.fc2 = _QLinear(hidden_fc, num_classes, bits=bits)

        def forward(self, x):
            def cb(conv, bn, x_in):
                return torch.relu(bn(conv(x_in)))
            h = cb(self.conv1, self.bn1, x)
            h = self.pool(cb(self.conv2, self.bn2, h))
            h = cb(self.conv3, self.bn3, h)
            h = self.pool(cb(self.conv4, self.bn4, h))
            h = h.reshape(h.size(0), -1)
            h = torch.relu(self.bn5(self.fc1(h)))
            return self.fc2(h)

    return PBNN_CNN, BNN_CNN, FP_CNN


# ---------------------------------------------------------------------------#
# Generic train/eval loop (works for any of the three models)                  #
# ---------------------------------------------------------------------------#

def _train_one(model, train_loader, test_loader, device, *,
               n_epochs: int, lr: float, label: str,
               metrics_csv: Path, is_pbnn: bool = False):
    """Train ``model`` for ``n_epochs`` and return (best_acc, history)."""
    import csv
    import torch
    from torch import nn
    from smtj_pbnn_sim.utils.logging import log
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    history = {"train_loss": [], "train_acc": [],
               "test_loss":  [], "test_acc":  [], "epoch_s": []}
    best_acc, best_state = 0.0, None

    for epoch in range(n_epochs):
        t0 = time.time()
        model.train()
        tr_loss_sum, tr_correct, n_seen = 0.0, 0, 0
        for x, y in train_loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            if is_pbnn:
                logits = model.forward_with_mode(
                    x, mode=ForwardMode.HARDWARE_AWARE)
            else:
                logits = model(x)
            loss = criterion(logits, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            tr_loss_sum += float(loss.item()) * x.size(0)
            tr_correct += int((logits.argmax(1) == y).sum().item())
            n_seen += x.size(0)

        model.eval()
        te_loss_sum, te_correct, n_te = 0.0, 0, 0
        with torch.no_grad():
            for x, y in test_loader:
                x = x.to(device, non_blocking=True)
                y = y.to(device, non_blocking=True)
                if is_pbnn:
                    logits = model.forward_with_mode(
                        x, mode=ForwardMode.HARDWARE_AWARE)
                else:
                    logits = model(x)
                te_loss_sum += float(criterion(logits, y).item()) * x.size(0)
                te_correct += int((logits.argmax(1) == y).sum().item())
                n_te += x.size(0)

        elapsed = time.time() - t0
        history["train_loss"].append(tr_loss_sum / max(1, n_seen))
        history["train_acc"].append(tr_correct / max(1, n_seen))
        history["test_loss"].append(te_loss_sum / max(1, n_te))
        history["test_acc"].append(te_correct / max(1, n_te))
        history["epoch_s"].append(elapsed)
        log(f"[{label:6s}] epoch {epoch + 1:02d}/{n_epochs}  "
            f"train acc={history['train_acc'][-1]:.4f}  "
            f"test acc={history['test_acc'][-1]:.4f}  ({elapsed:.1f}s)")

        if history["test_acc"][-1] > best_acc:
            best_acc = history["test_acc"][-1]
            best_state = {k: v.detach().clone()
                          for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    with open(metrics_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "train_loss", "train_acc",
                    "test_loss", "test_acc", "elapsed_s"])
        for e in range(n_epochs):
            w.writerow([e + 1,
                        f"{history['train_loss'][e]:.6f}",
                        f"{history['train_acc'][e]:.6f}",
                        f"{history['test_loss'][e]:.6f}",
                        f"{history['test_acc'][e]:.6f}",
                        f"{history['epoch_s'][e]:.2f}"])

    return best_acc, history


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

    import shutil
    from smtj_pbnn_sim.data.fashion_mnist import get_fashion_mnist_loaders
    from smtj_pbnn_sim.device.variation import VariationConfig
    from smtj_pbnn_sim.nn.pbnn_linear import DeviceLayerParams, PBNNLinear
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.utils.seeding import set_global_seed

    out_dir = make_run_dir(
        "05a_fashion_mnist_pbnn_cnn", base=REPO / "runs")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    train_loader, test_loader = get_fashion_mnist_loaders(
        root="./data/fashion_mnist", batch_size=BATCH, num_workers=0)

    # ----- Device parameters (Chapter 2.3 primary reference) -----
    dp = DeviceLayerParams(
        V_th_nom=0.894, V_T_nom=1.0 / 44.6,
        R_P_nom=4.9e3, TMR_nom=1.0, R_SOT_nom=776.0,
        Delta_nom=4.91, V_c0_nom=0.857,
        eta_c=5.34, tau_0=1.0e-9, t_p=0.75e-9,
    )
    vc = VariationConfig(mode="delta", cv_delta=0.077,
                         sigma_RP_rel=0.05, sigma_TMR_rel=0.10, seed=42)

    PBNN_CNN, BNN_CNN, FP_CNN = _make_models(
        device_params=dp, variation_cfg=vc, T_full_stack=T_FULL_STACK)

    # ----- Part 1: PBNN-CNN -----
    print("=" * 70)
    print("Part 1: Training PBNN-CNN (sMTJ binary, HARDWARE_AWARE)")
    print("=" * 70)
    set_global_seed(0)
    pbnn = PBNN_CNN().to(device)
    n_params = sum(p.numel() for p in pbnn.parameters())
    print(f"  PBNN-CNN parameters: {n_params/1e6:.2f} M")
    pbnn_best, pbnn_hist = _train_one(
        pbnn, train_loader, test_loader, device,
        n_epochs=EPOCHS, lr=LR, label="PBNN",
        metrics_csv=out_dir / "metrics.csv", is_pbnn=True)

    # Theta-scale post-processing: same trick as exp 05.
    theta_scale = 100.0
    with torch.no_grad():
        from smtj_pbnn_sim.nn.pbnn_conv import PBNNConv2d
        for m in pbnn.modules():
            if isinstance(m, (PBNNLinear, PBNNConv2d)):
                m.theta.mul_(theta_scale)
    torch.save({"model_state": pbnn.state_dict(),
                "config": {
                    "model": {"base_ch": BASE_CH, "hidden_fc": HIDDEN_FC,
                              "num_classes": NUM_CLASSES},
                    "data":  {"batch_size": BATCH},
                    "T_full_stack": T_FULL_STACK,
                    "device": {
                        "operating_point": {"V_th_nom": dp.V_th_nom,
                                             "V_T_nom":  dp.V_T_nom,
                                             "t_p":      dp.t_p},
                        "neel_brown":      {"Delta_nom": dp.Delta_nom,
                                             "V_c0_nom":  dp.V_c0_nom,
                                             "tau_0":     dp.tau_0},
                        "eta_c": dp.eta_c,
                        "resistance":      {"R_P_nom":  dp.R_P_nom,
                                             "TMR_nom":  dp.TMR_nom,
                                             "R_SOT":    dp.R_SOT_nom},
                    },
                },
                "best_acc": pbnn_best,
                "theta_scale": theta_scale},
               out_dir / "best.pt")

    stable_dir = REPO / "runs" / "fashion_mnist_pbnn_cnn"
    stable_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_dir / "best.pt", stable_dir / "best.pt")

    # ----- Part 2: BNN-CNN baseline -----
    print("\n" + "=" * 70)
    print("Part 2: Training BNN-CNN baseline (sign-STE, no sMTJ)")
    print("=" * 70)
    set_global_seed(0)
    bnn = BNN_CNN().to(device)
    bnn_best, bnn_hist = _train_one(
        bnn, train_loader, test_loader, device,
        n_epochs=EPOCHS, lr=LR, label="BNN",
        metrics_csv=out_dir / "bnn_metrics.csv", is_pbnn=False)

    # ----- Part 3: FP/INT-QAT baselines -----
    fp_bits = [32, 8]
    fp_hists: dict[int, dict] = {}
    fp_bests: dict[int, float] = {}
    for bits in fp_bits:
        label = "FP32" if bits >= 32 else f"INT{bits}"
        print("\n" + "=" * 70)
        print(f"Part 3: Training FP-CNN baseline ({label})")
        print("=" * 70)
        set_global_seed(0)
        fp = FP_CNN(bits=bits).to(device)
        fp_bests[bits], fp_hists[bits] = _train_one(
            fp, train_loader, test_loader, device,
            n_epochs=EPOCHS, lr=LR, label=label,
            metrics_csv=out_dir / f"fp_{label.lower()}_metrics.csv",
            is_pbnn=False)

    # ----- Part 4: plot training curves -----
    print("\n" + "=" * 70)
    print("Part 4: Generating training-curve figure")
    print("=" * 70)
    fp_colors = {32: "#1F2937", 8: "#475569"}
    fp_label = lambda b: ("FP-CNN FP32 (ideal)" if b >= 32
                          else f"FP-CNN INT{b} (QAT)")
    bnn_color = "#D97706"

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    epochs = list(range(1, EPOCHS + 1))

    ax = axes[0]
    ax.plot(epochs, [a * 100 for a in pbnn_hist["test_acc"]], "o-",
            color="#4B1369", lw=2.2, markersize=5,
            label="PBNN-CNN (binary ±1, sMTJ)")
    ax.plot(epochs, [a * 100 for a in bnn_hist["test_acc"]], "s-",
            color=bnn_color, lw=2.0, markersize=4.5,
            label="BNN-CNN (digital, sign-STE)")
    for bits in fp_bits:
        ax.plot(epochs, [a * 100 for a in fp_hists[bits]["test_acc"]],
                "D-", color=fp_colors[bits], lw=1.8, markersize=4,
                label=fp_label(bits))
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Test accuracy (%)", fontsize=12)
    ax.set_title("Fashion-MNIST test accuracy vs epoch", fontsize=13)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax.plot(epochs, pbnn_hist["test_loss"], "o-",
            color="#4B1369", lw=2.2, markersize=5,
            label="PBNN-CNN (binary ±1, sMTJ)")
    ax.plot(epochs, bnn_hist["test_loss"], "s-",
            color=bnn_color, lw=2.0, markersize=4.5,
            label="BNN-CNN (digital, sign-STE)")
    for bits in fp_bits:
        ax.plot(epochs, fp_hists[bits]["test_loss"],
                "D-", color=fp_colors[bits], lw=1.8, markersize=4,
                label=fp_label(bits))
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Test loss", fontsize=12)
    ax.set_title("Fashion-MNIST test loss vs epoch", fontsize=13)
    ax.set_yscale("log")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3, which="both")

    fig.suptitle(
        "Fashion-MNIST PBNN-CNN vs BNN-CNN vs FP-CNN — same topology, "
        f"same training ({EPOCHS} epochs, Adam lr={LR}, "
        f"base_ch={BASE_CH}, batch={BATCH})",
        fontsize=12, y=1.02)
    fig.tight_layout()
    out_fig = REPO / "figures" / "05a_fashion_mnist_training_curves.png"
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    shutil.copy2(out_fig,
                 out_dir / "05a_fashion_mnist_training_curves.png")
    print(f"  Figure saved: {out_fig.relative_to(REPO)}")

    # ----- Summary -----
    print("\n--- Summary ---")
    print(f"  PBNN-CNN (binary ±1, sMTJ)  best test acc = "
          f"{pbnn_best * 100:.2f}%")
    print(f"  BNN-CNN  (digital sign-STE) best test acc = "
          f"{bnn_best * 100:.2f}%")
    for bits in fp_bits:
        label = "FP32" if bits >= 32 else f"INT{bits}"
        print(f"  FP-CNN   {label:5s}              best test acc = "
              f"{fp_bests[bits] * 100:.2f}%")
    print(f"\nRun directory: {out_dir}")
    print(f"Stable PBNN checkpoint: {stable_dir / 'best.pt'}")
    print("Done.")


if __name__ == "__main__":
    main()
