"""05 -- MNIST PBNN-MLP training, with FP-MLP baseline comparison.

Trains the 3-layer PBNN-MLP defined in
``smtj_pbnn_sim.scripts._mnist_train`` using the Chapter-2.3 primary-
reference device parameters and PDK-baseline variation, then trains a
matched-architecture full-precision MLP under identical hyper-parameters
(Adam lr=1e-3, batch 128, 20 epochs, hidden=1024) so the per-epoch
training curves can be compared.

Demonstrates that **PBNN converges to FP-comparable accuracy at the
same epoch count** even though every weight is binary at inference.

Outputs:
  - runs/05_mnist_pbnn_<ts>/{best.pt, metrics.csv, summary.json}
                                                 (PBNN, via the CLI run())
  - runs/05_mnist_pbnn_<ts>/fp_metrics.csv       FP-MLP per-epoch metrics
  - figures/05_mnist_training_curves.png         2-panel: accuracy + loss
                                                 vs epoch, PBNN vs FP-MLP
  - runs/mnist_pbnn_mlp/best.pt                  stable copy for downstream
                                                 experiments

Run from the repo root:

    python experiments/05_mnist_pbnn.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def _train_quantized_fp(out_dir: Path, hidden: int, n_epochs: int,
                          batch_size: int, lr: float, bits: int):
    """Train an FP-MLP baseline at a given weight bit-width via QAT.

    bits >= 32 => float32 (no quantization).
    bits  < 32 => symmetric INT-N QAT with straight-through estimator
                   on weights (activations stay fp32).

    Returns a dict with per-epoch lists: train_loss/acc, test_loss/acc.
    """
    import csv
    import torch
    from torch import nn
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.logging import log

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_global_seed(0)
    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=batch_size, num_workers=0)

    class QuantizeSTE(torch.autograd.Function):
        """Symmetric INT-N quantization with straight-through gradient."""
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

    class QuantizedLinear(nn.Linear):
        """nn.Linear with QAT on weights."""
        def __init__(self, in_features, out_features, bits, bias=True):
            super().__init__(in_features, out_features, bias=bias)
            self.bits = bits
        def forward(self, x):
            w_q = QuantizeSTE.apply(self.weight, self.bits)
            return torch.nn.functional.linear(x, w_q, self.bias)

    class FP_MLP(nn.Module):
        def __init__(self, hidden=1024, bits=32):
            super().__init__()
            self.fc1 = QuantizedLinear(28 * 28, hidden, bits=bits)
            self.bn1 = nn.BatchNorm1d(hidden)
            self.fc2 = QuantizedLinear(hidden, hidden, bits=bits)
            self.bn2 = nn.BatchNorm1d(hidden)
            self.fc3 = QuantizedLinear(hidden, 10, bits=bits)
        def forward(self, x):
            x = x.view(x.size(0), -1)
            h = torch.relu(self.bn1(self.fc1(x)))
            h = torch.relu(self.bn2(self.fc2(h)))
            return self.fc3(h)

    label = "FP32" if bits >= 32 else f"INT{bits}"
    model = FP_MLP(hidden=hidden, bits=bits).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    history = {"train_loss": [], "train_acc": [],
               "test_loss":  [], "test_acc":  [], "epoch_s": []}

    for epoch in range(n_epochs):
        t0 = time.time()
        model.train()
        tr_loss_sum, tr_correct, n_seen = 0.0, 0, 0
        for x, y in train_loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
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
        log(f"[{label:5s}] epoch {epoch + 1:02d}/{n_epochs}  "
            f"train acc={history['train_acc'][-1]:.4f}  "
            f"test acc={history['test_acc'][-1]:.4f}  ({elapsed:.1f}s)")

    # Save metrics CSV
    csv_path = out_dir / f"fp_{label.lower()}_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
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
    return history


def _load_pbnn_metrics(metrics_csv: Path):
    """Load per-epoch PBNN metrics from MetricsLogger CSV."""
    import csv
    h = {"train_loss": [], "train_acc": [],
         "test_loss":  [], "test_acc":  []}
    with open(metrics_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h["train_loss"].append(float(row["train_loss"]))
            h["train_acc"].append(float(row["train_acc"]))
            h["test_loss"].append(float(row["test_loss"]))
            h["test_acc"].append(float(row["test_acc"]))
    return h


def main() -> None:
    try:
        import torch  # noqa: F401
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("PyTorch + matplotlib + numpy required.")
        print("Install with: pip install torch torchvision matplotlib")
        sys.exit(1)

    import shutil
    from smtj_pbnn_sim.utils.io import load_yaml, make_run_dir
    from smtj_pbnn_sim.scripts._mnist_train import run

    cfg_path = REPO / "configs" / "experiment" / "mnist_lenet.yaml"
    cfg = load_yaml(cfg_path)
    out_dir = make_run_dir("05_mnist_pbnn", base=REPO / "runs")

    # ----- Part 1: train PBNN-MLP via the CLI run() -----
    print("=" * 70)
    print("Part 1: Training PBNN-MLP")
    print("=" * 70)
    ret = run(cfg, out_dir)

    # Copy best.pt to stable location for downstream experiments
    stable = REPO / "runs" / "mnist_pbnn_mlp"
    stable.mkdir(parents=True, exist_ok=True)
    best_src = out_dir / "best.pt"
    if best_src.exists():
        shutil.copy2(best_src, stable / "best.pt")

    if ret != 0:
        sys.exit(ret)

    # ----- Part 2: train matched FP-MLP baselines at multiple bit widths -
    print("\n" + "=" * 70)
    print("Part 2: Training matched FP-MLP baselines (FP32 + INT8/4/2 QAT)")
    print("=" * 70)
    n_epochs = int(cfg.get("epochs", 20))
    hidden = int(cfg.get("model", {}).get("hidden", 1024))
    batch = int(cfg.get("data", {}).get("batch_size", 128))
    lr = float(cfg.get("optim", {}).get("lr", 1e-3))

    # bit widths to compare: 32 (ideal), 8 (typical digital CIM), 4, 2
    fp_bit_widths = [32, 8, 4, 2]
    fp_histories: dict[int, dict] = {}
    for bits in fp_bit_widths:
        label = "FP32" if bits >= 32 else f"INT{bits}"
        print(f"\n--- Training FP-MLP at {label} ---")
        fp_histories[bits] = _train_quantized_fp(
            out_dir, hidden=hidden, n_epochs=n_epochs,
            batch_size=batch, lr=lr, bits=bits)

    # ----- Part 3: load PBNN metrics and plot training curves -----
    print("\n" + "=" * 70)
    print("Part 3: Generating training-curve figure")
    print("=" * 70)
    pbnn_history = _load_pbnn_metrics(out_dir / "metrics.csv")

    # Color palette: PBNN dark purple; FP curves shade from dark grey
    # (FP32, ideal) to a warmer tone (INT2, aggressive)
    fp_colors = {32: "#1F2937", 8: "#475569", 4: "#A16207", 2: "#B91C1C"}
    fp_label = lambda b: ("FP-MLP FP32 (ideal)" if b >= 32
                          else f"FP-MLP INT{b} (QAT)")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    epochs = list(range(1, n_epochs + 1))

    # Accuracy panel
    ax = axes[0]
    ax.plot(epochs, [a * 100 for a in pbnn_history["test_acc"]], "o-",
            color="#4B1369", lw=2.2, markersize=5,
            label=f"PBNN-MLP (binary ±1)")
    for bits in fp_bit_widths:
        h = fp_histories[bits]
        ax.plot(epochs, [a * 100 for a in h["test_acc"]], "D-",
                color=fp_colors[bits], lw=1.8, markersize=4,
                label=fp_label(bits))
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Test accuracy (%)", fontsize=12)
    ax.set_title("Test accuracy vs epoch", fontsize=13)
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_ylim(70, 100)

    # Loss panel
    ax = axes[1]
    ax.plot(epochs, pbnn_history["test_loss"], "o-",
            color="#4B1369", lw=2.2, markersize=5,
            label="PBNN-MLP (binary ±1)")
    for bits in fp_bit_widths:
        h = fp_histories[bits]
        ax.plot(epochs, h["test_loss"], "D-",
                color=fp_colors[bits], lw=1.8, markersize=4,
                label=fp_label(bits))
    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("Test loss", fontsize=12)
    ax.set_title("Test loss vs epoch", fontsize=13)
    ax.set_yscale("log")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3, which="both")

    fig.suptitle(
        "MNIST PBNN-MLP vs FP-MLP across bit widths — same architecture, "
        f"same training ({n_epochs} epochs, Adam lr={lr}, hidden={hidden}, "
        f"batch={batch})",
        fontsize=13, y=1.02)
    fig.tight_layout()
    out_fig = REPO / "figures" / "05_mnist_training_curves.png"
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    shutil.copy2(out_fig, out_dir / "05_mnist_training_curves.png")
    print(f"  Figure saved: {out_fig.relative_to(REPO)}")

    # ----- Summary -----
    pbnn_best = max(pbnn_history["test_acc"])
    print("\n--- Summary ---")
    print(f"  PBNN-MLP (binary ±1) best test acc = {pbnn_best * 100:.2f}%  "
          f"(final = {pbnn_history['test_acc'][-1] * 100:.2f}%)")
    for bits in fp_bit_widths:
        h = fp_histories[bits]
        best = max(h["test_acc"])
        label = "FP32" if bits >= 32 else f"INT{bits}"
        print(f"  FP-MLP {label:5s}             best test acc = "
              f"{best * 100:.2f}%  (final = {h['test_acc'][-1] * 100:.2f}%)")

    # Where does PBNN sit in the FP bit-width ladder?
    fp_int4_best = max(fp_histories[4]["test_acc"])
    fp_int2_best = max(fp_histories[2]["test_acc"])
    if fp_int2_best <= pbnn_best <= fp_int4_best:
        verdict = (f"PBNN sits between INT2 ({fp_int2_best * 100:.2f}%) "
                   f"and INT4 ({fp_int4_best * 100:.2f}%) in the bit-width ladder.")
    elif pbnn_best > fp_int4_best:
        verdict = (f"PBNN ({pbnn_best * 100:.2f}%) BEATS FP-MLP INT4 "
                   f"({fp_int4_best * 100:.2f}%) at the same epoch budget.")
    else:
        verdict = (f"PBNN ({pbnn_best * 100:.2f}%) trails FP-MLP INT2 "
                   f"({fp_int2_best * 100:.2f}%) — unexpected, investigate.")
    print(f"\n  → {verdict}")
    print(f"\nRun directory: {out_dir}")
    print("Done.")


if __name__ == "__main__":
    main()
