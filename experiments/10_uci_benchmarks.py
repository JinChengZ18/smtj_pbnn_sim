"""10 -- UCI benchmark suite: PBNN-MLP across diverse tabular datasets.

Tests PBNN-MLP adaptability beyond MNIST on six classic UCI tabular
datasets covering different scales and difficulty levels:

  - Iris      :  150 samples,  4 features,  3 classes  (toy)
  - WDBC      :  569 samples, 30 features,  2 classes  (medical)
  - Yeast     : 1484 samples,  8 features, 10 classes  (multiclass, hard)
  - Vehicle   :  846 samples, 18 features,  4 classes  (image features)
  - Spambase  : 4601 samples, 57 features,  2 classes  (text features)
  - Satimage  : 6435 samples, 36 features,  6 classes  (remote sensing)

For each dataset, trains:
  - A PBNN-MLP with HARDWARE_AWARE forward (the deployment target)
  - A full-precision (FP) MLP with the same topology (FP baseline)

Both models use the same architecture (2 hidden layers + output, hidden
width = 64), the same optimizer (Adam, lr=1e-3), and the same training
schedule. A horizontal reference line marks a typical literature
baseline accuracy for each dataset.

Produces:
  - figures/10_uci_accuracy_curves.png   accuracy vs epoch (2x3 grid)
  - figures/10_uci_residual_curves.png   cross-entropy loss vs epoch (2x3 grid)
  - runs/10_uci_<ts>/<dataset>_history.csv  per-epoch metrics
  - runs/10_uci_<ts>/summary.csv         final accuracy table

Run from the repo root:

    python experiments/10_uci_benchmarks.py

Note: requires internet on the first run to download datasets from the
UCI repository.  Subsequent runs are offline (cached under data/uci/).
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Models                                                                     #
# ---------------------------------------------------------------------------#

def _make_models():
    """Import-gated definitions of the two MLPs (require torch)."""
    import torch
    from torch import Tensor

    from smtj_pbnn_sim.nn.pbnn_linear import (
        PBNNLinear, ForwardMode, DeviceLayerParams,
    )
    from smtj_pbnn_sim.nn.batchnorm import BinaryBatchNorm1d
    from smtj_pbnn_sim.nn.ste import sign_ste

    class PBNN_MLP_Tabular(torch.nn.Module):
        """Generic 2-hidden-layer PBNN MLP for tabular data."""

        def __init__(self, in_dim: int, hidden: int, num_classes: int):
            super().__init__()
            kw = dict(device_params=DeviceLayerParams(),
                      variation_cfg=None, T_full_stack=8)
            self.fc1 = PBNNLinear(in_dim, hidden, binarize_output=False, **kw)
            self.bn1 = BinaryBatchNorm1d(hidden)
            self.fc2 = PBNNLinear(hidden, hidden, binarize_output=False, **kw)
            self.bn2 = BinaryBatchNorm1d(hidden)
            self.fc3 = PBNNLinear(hidden, num_classes,
                                   binarize_output=False, **kw)

        def forward_with_mode(self, x: Tensor, *,
                               mode=ForwardMode.HARDWARE_AWARE,
                               T: int | None = None) -> Tensor:
            h = self.fc1(x, mode=mode, T=T, sample=False)
            h = self.bn1(h); h = sign_ste(h)
            h = self.fc2(h, mode=mode, T=T, sample=False)
            h = self.bn2(h); h = sign_ste(h)
            return self.fc3(h, mode=mode, T=T, sample=False)

        def forward(self, x: Tensor) -> Tensor:
            return self.forward_with_mode(x)

    class FP_MLP_Tabular(torch.nn.Module):
        """Full-precision baseline with identical topology."""

        def __init__(self, in_dim: int, hidden: int, num_classes: int):
            super().__init__()
            self.fc1 = torch.nn.Linear(in_dim, hidden)
            self.bn1 = torch.nn.BatchNorm1d(hidden)
            self.fc2 = torch.nn.Linear(hidden, hidden)
            self.bn2 = torch.nn.BatchNorm1d(hidden)
            self.fc3 = torch.nn.Linear(hidden, num_classes)

        def forward(self, x: Tensor) -> Tensor:
            h = torch.relu(self.bn1(self.fc1(x)))
            h = torch.relu(self.bn2(self.fc2(h)))
            return self.fc3(h)

    return PBNN_MLP_Tabular, FP_MLP_Tabular


# ---------------------------------------------------------------------------#
# Training loop                                                              #
# ---------------------------------------------------------------------------#

def _train(model, X_tr, y_tr, X_te, y_te, *,
           n_epochs: int, batch_size: int, lr: float, device):
    """Train one model and return per-epoch history."""
    import torch
    import torch.nn.functional as F

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    history = {"train_loss": [], "train_acc": [],
               "test_loss": [],  "test_acc": []}
    n = X_tr.shape[0]

    for _ in range(n_epochs):
        model.train()
        perm = torch.randperm(n, device=device)
        tr_loss_sum, tr_correct = 0.0, 0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            xb, yb = X_tr[idx], y_tr[idx]
            if xb.size(0) < 2:  # BN needs >= 2 samples
                continue
            logits = model(xb)
            loss = F.cross_entropy(logits, yb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            tr_loss_sum += loss.item() * yb.size(0)
            tr_correct += int((logits.argmax(1) == yb).sum().item())
        history["train_loss"].append(tr_loss_sum / max(1, n))
        history["train_acc"].append(tr_correct / max(1, n))

        model.eval()
        with torch.no_grad():
            logits_te = model(X_te)
            te_loss = F.cross_entropy(logits_te, y_te).item()
            te_acc = (logits_te.argmax(1) == y_te).float().mean().item()
        history["test_loss"].append(te_loss)
        history["test_acc"].append(te_acc)

    return history


# ---------------------------------------------------------------------------#
# Main experiment                                                            #
# ---------------------------------------------------------------------------#

# Typical literature baseline accuracies (general MLP / classical ML).
# These are not strict SOTA numbers but commonly cited reference levels
# achievable with shallow networks or strong classical models.
SOTA_BASELINES = {
    "iris":     0.967,   # k-NN, Random Forest (typical)
    "wdbc":     0.965,   # SVM, logistic regression (typical)
    "yeast":    0.620,   # MLP, RF (notoriously hard)
    "vehicle":  0.840,   # SVM, RF (Statlog comparison study)
    "spambase": 0.940,   # Random Forest, GBM (typical)
    "satimage": 0.910,   # k-NN, MLP (Statlog comparison study)
}

# Per-dataset training hyper-parameters (tuned for size & difficulty).
DATASET_CFG = {
    "iris":     dict(hidden=32,  n_epochs=120, batch_size=16, lr=1e-3),
    "wdbc":     dict(hidden=64,  n_epochs=120, batch_size=32, lr=1e-3),
    "yeast":    dict(hidden=64,  n_epochs=200, batch_size=32, lr=1e-3),
    "vehicle":  dict(hidden=64,  n_epochs=200, batch_size=32, lr=1e-3),
    "spambase": dict(hidden=128, n_epochs=120, batch_size=64, lr=1e-3),
    "satimage": dict(hidden=128, n_epochs=120, batch_size=64, lr=1e-3),
}


def main() -> None:
    try:
        import torch
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("PyTorch, matplotlib, and numpy are required for this experiment.")
        sys.exit(1)

    import csv
    import shutil
    from smtj_pbnn_sim.data.uci import DATASETS
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    PBNN_MLP_Tabular, FP_MLP_Tabular = _make_models()

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("10_uci", base=REPO / "runs")

    print("=== Experiment 10: UCI tabular benchmarks ===\n")
    print(f"Device: {device}")
    print(f"Run dir: {run_dir}\n")

    all_history: dict[str, dict] = {}
    summary_rows = []

    for name, (loader, desc) in DATASETS.items():
        print(f"--- {desc} ---")
        cfg = DATASET_CFG[name]
        X, y, classes = loader()
        n_classes = len(classes)
        in_dim = X.shape[1]

        # 70/30 stratified train/test split
        rng = np.random.default_rng(42)
        idx_by_cls = [np.where(y == c)[0] for c in range(n_classes)]
        train_idx, test_idx = [], []
        for ci in idx_by_cls:
            rng.shuffle(ci)
            cut = int(0.7 * len(ci))
            train_idx.extend(ci[:cut].tolist())
            test_idx.extend(ci[cut:].tolist())
        train_idx = np.array(train_idx); test_idx = np.array(test_idx)
        rng.shuffle(train_idx); rng.shuffle(test_idx)

        # Standardize features using train mean/std
        mu = X[train_idx].mean(0, keepdims=True)
        sd = X[train_idx].std(0, keepdims=True) + 1e-8
        X_norm = (X - mu) / sd

        X_tr = torch.from_numpy(X_norm[train_idx]).float().to(device)
        y_tr = torch.from_numpy(y[train_idx]).long().to(device)
        X_te = torch.from_numpy(X_norm[test_idx]).float().to(device)
        y_te = torch.from_numpy(y[test_idx]).long().to(device)

        # Train PBNN
        set_global_seed(42)
        pbnn = PBNN_MLP_Tabular(in_dim, cfg["hidden"], n_classes).to(device)
        t0 = time.time()
        h_pbnn = _train(pbnn, X_tr, y_tr, X_te, y_te,
                        n_epochs=cfg["n_epochs"], batch_size=cfg["batch_size"],
                        lr=cfg["lr"], device=device)
        t_pbnn = time.time() - t0

        # Train FP
        set_global_seed(42)
        fp = FP_MLP_Tabular(in_dim, cfg["hidden"], n_classes).to(device)
        t0 = time.time()
        h_fp = _train(fp, X_tr, y_tr, X_te, y_te,
                      n_epochs=cfg["n_epochs"], batch_size=cfg["batch_size"],
                      lr=cfg["lr"], device=device)
        t_fp = time.time() - t0

        best_pbnn = max(h_pbnn["test_acc"])
        best_fp = max(h_fp["test_acc"])
        baseline = SOTA_BASELINES[name]

        print(f"  PBNN best test acc = {best_pbnn:.4f}  ({t_pbnn:.1f}s)")
        print(f"  FP-MLP best test acc = {best_fp:.4f}  ({t_fp:.1f}s)")
        print(f"  Reference baseline   = {baseline:.4f}\n")

        all_history[name] = {"pbnn": h_pbnn, "fp": h_fp,
                             "n_train": len(train_idx),
                             "n_test": len(test_idx),
                             "in_dim": in_dim,
                             "n_classes": n_classes}
        summary_rows.append([name, in_dim, n_classes, len(train_idx),
                             len(test_idx),
                             f"{best_pbnn:.4f}", f"{best_fp:.4f}",
                             f"{baseline:.4f}"])

        # Save per-dataset history CSV
        csv_path = run_dir / f"{name}_history.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["epoch",
                        "pbnn_train_loss", "pbnn_train_acc",
                        "pbnn_test_loss",  "pbnn_test_acc",
                        "fp_train_loss",   "fp_train_acc",
                        "fp_test_loss",    "fp_test_acc"])
            for e in range(cfg["n_epochs"]):
                w.writerow([
                    e + 1,
                    f"{h_pbnn['train_loss'][e]:.6f}",
                    f"{h_pbnn['train_acc'][e]:.6f}",
                    f"{h_pbnn['test_loss'][e]:.6f}",
                    f"{h_pbnn['test_acc'][e]:.6f}",
                    f"{h_fp['train_loss'][e]:.6f}",
                    f"{h_fp['train_acc'][e]:.6f}",
                    f"{h_fp['test_loss'][e]:.6f}",
                    f"{h_fp['test_acc'][e]:.6f}",
                ])

    # Save summary
    with open(run_dir / "summary.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dataset", "in_dim", "num_classes",
                    "n_train", "n_test",
                    "pbnn_best_acc", "fp_best_acc",
                    "ref_baseline"])
        w.writerows(summary_rows)
    print("Summary CSV saved.")

    # ----- Plot accuracy curves (2x3 grid) -----
    fig_a, axes_a = plt.subplots(2, 3, figsize=(16, 9))
    axes_a = axes_a.ravel()
    for idx, (name, (loader, desc)) in enumerate(DATASETS.items()):
        ax = axes_a[idx]
        h = all_history[name]
        epochs = np.arange(1, len(h["pbnn"]["test_acc"]) + 1)
        ax.plot(epochs, [a * 100 for a in h["pbnn"]["test_acc"]],
                "-", color="#4B1369", lw=2, label="PBNN test")
        ax.plot(epochs, [a * 100 for a in h["pbnn"]["train_acc"]],
                "--", color="#A97DBE", lw=1.2, alpha=0.8,
                label="PBNN train")
        ax.plot(epochs, [a * 100 for a in h["fp"]["test_acc"]],
                "-", color="#6B7280", lw=2, label="FP-MLP test")
        ax.plot(epochs, [a * 100 for a in h["fp"]["train_acc"]],
                "--", color="#9CA3AF", lw=1.2, alpha=0.8,
                label="FP-MLP train")
        baseline = SOTA_BASELINES[name] * 100
        ax.axhline(baseline, color="#D97706", ls=":", lw=1.5,
                   label=f"Reference {baseline:.1f}%")
        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel("Accuracy (%)", fontsize=11)
        ax.set_title(f"{desc}", fontsize=12)
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 105)

    fig_a.suptitle("UCI tabular benchmarks: accuracy vs training epoch",
                   fontsize=15, y=0.99)
    fig_a.tight_layout(rect=[0, 0, 1, 0.97])
    out_a = REPO / "figures" / "10_uci_accuracy_curves.png"
    out_a.parent.mkdir(parents=True, exist_ok=True)
    fig_a.savefig(out_a, dpi=150, bbox_inches="tight")
    shutil.copy2(out_a, run_dir / "10_uci_accuracy_curves.png")
    print(f"Figure A saved: {out_a.relative_to(REPO)}")

    # ----- Plot residual (loss) curves (2x3 grid) -----
    fig_b, axes_b = plt.subplots(2, 3, figsize=(16, 9))
    axes_b = axes_b.ravel()
    for idx, (name, (loader, desc)) in enumerate(DATASETS.items()):
        ax = axes_b[idx]
        h = all_history[name]
        epochs = np.arange(1, len(h["pbnn"]["test_loss"]) + 1)
        ax.plot(epochs, h["pbnn"]["test_loss"], "-",
                color="#4B1369", lw=2, label="PBNN test loss")
        ax.plot(epochs, h["pbnn"]["train_loss"], "--",
                color="#A97DBE", lw=1.2, alpha=0.8, label="PBNN train loss")
        ax.plot(epochs, h["fp"]["test_loss"], "-",
                color="#6B7280", lw=2, label="FP-MLP test loss")
        ax.plot(epochs, h["fp"]["train_loss"], "--",
                color="#9CA3AF", lw=1.2, alpha=0.8, label="FP-MLP train loss")
        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel("Cross-entropy residual", fontsize=11)
        ax.set_title(f"{desc}", fontsize=12)
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.3)
        ax.set_yscale("log")

    fig_b.suptitle("UCI tabular benchmarks: residual (cross-entropy) vs training epoch",
                   fontsize=15, y=0.99)
    fig_b.tight_layout(rect=[0, 0, 1, 0.97])
    out_b = REPO / "figures" / "10_uci_residual_curves.png"
    fig_b.savefig(out_b, dpi=150, bbox_inches="tight")
    shutil.copy2(out_b, run_dir / "10_uci_residual_curves.png")
    print(f"Figure B saved: {out_b.relative_to(REPO)}")

    # ----- Summary table -----
    print("\n--- Summary ---")
    print(f"{'Dataset':10s} {'in_dim':>7} {'classes':>8} "
          f"{'n_train':>8} {'n_test':>7}  "
          f"{'PBNN':>8} {'FP':>8} {'Ref':>8}")
    print("-" * 75)
    for row in summary_rows:
        print(f"{row[0]:10s} {row[1]:>7} {row[2]:>8} {row[3]:>8} "
              f"{row[4]:>7}  {row[5]:>8} {row[6]:>8} {row[7]:>8}")
    print("\nDone.")


if __name__ == "__main__":
    main()
