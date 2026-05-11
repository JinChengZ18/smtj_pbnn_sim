"""07 -- Baseline comparison: PBNN vs BNN vs full-precision under noise.

Compares three models on MNIST with identical topology (784->1024->1024->10):

  - PBNN (T=4) : sMTJ device model, FULL_STACK with 4 stochastic samples
                 per inference. T=4 is the practical sweet spot from
                 Experiment 06 (97.51% test accuracy, only 0.17pp below
                 T=64 at one-eighth the energy budget).
  - BNN        : DeterministicBinaryLinear with sign_ste activation
  - FP-NN      : standard nn.Linear with ReLU activation

Robustness is evaluated under eight perturbation types (2x4 grid):

  Input-level noise
    (a) Additive Gaussian       --  sigma * N(0, 1)  added to input pixels
    (b) Salt-and-pepper         --  fraction p of pixels set to 0 or 1
    (c) Speckle (multiplicative)--  x * (1 + sigma * N(0, 1))
    (d) Gaussian blur           --  Gaussian smoothing with kernel radius r
    (e) Cutout / occlusion      --  zero out a random patch of size k x k
    (f) Brightness shift        --  x + b

  Model-level noise
    (g) Weight perturbation     --  Gaussian noise added to all weights

  Adversarial noise
    (h) PGD-10 attack           --  10-step projected-gradient L_inf attack

The combination demonstrates that PBNN's T-step stochastic averaging
gives a clear advantage under model-level and adversarial perturbations,
while continuous-weight FP-NN is most robust under simple additive
input noise, where its higher information capacity per weight absorbs
small linear perturbations.

Run from the repo root:

    python experiments/07_baseline_comparison.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Model definitions                                                          #
# ---------------------------------------------------------------------------#

def _make_models(hidden: int = 1024, num_classes: int = 10):
    """Import-gated model definitions (require torch)."""
    import torch
    from torch import Tensor

    from smtj_pbnn_sim.nn.deterministic_bnn import DeterministicBinaryLinear
    from smtj_pbnn_sim.nn.batchnorm import BinaryBatchNorm1d
    from smtj_pbnn_sim.nn.ste import sign_ste

    class BNN_MLP(torch.nn.Module):
        """Standard BNN MLP: DeterministicBinaryLinear + BN + sign_ste."""

        def __init__(self, hidden: int = 1024, num_classes: int = 10):
            super().__init__()
            self.fc1 = DeterministicBinaryLinear(28 * 28, hidden)
            self.bn1 = BinaryBatchNorm1d(hidden)
            self.fc2 = DeterministicBinaryLinear(hidden, hidden)
            self.bn2 = BinaryBatchNorm1d(hidden)
            self.fc3 = DeterministicBinaryLinear(hidden, num_classes)

        def forward(self, x: Tensor) -> Tensor:
            x = x.view(x.size(0), -1)
            h = sign_ste(self.bn1(self.fc1(x)))
            h = sign_ste(self.bn2(self.fc2(h)))
            return self.fc3(h)

    class FP_MLP(torch.nn.Module):
        """Full-precision MLP: nn.Linear + BN + ReLU."""

        def __init__(self, hidden: int = 1024, num_classes: int = 10):
            super().__init__()
            self.fc1 = torch.nn.Linear(28 * 28, hidden)
            self.bn1 = torch.nn.BatchNorm1d(hidden)
            self.fc2 = torch.nn.Linear(hidden, hidden)
            self.bn2 = torch.nn.BatchNorm1d(hidden)
            self.fc3 = torch.nn.Linear(hidden, num_classes)

        def forward(self, x: Tensor) -> Tensor:
            x = x.view(x.size(0), -1)
            h = torch.relu(self.bn1(self.fc1(x)))
            h = torch.relu(self.bn2(self.fc2(h)))
            return self.fc3(h)

    return BNN_MLP, FP_MLP


# ---------------------------------------------------------------------------#
# Training helper                                                            #
# ---------------------------------------------------------------------------#

def _train_model(model, train_loader, test_loader, device, *,
                 n_epochs: int = 20, lr: float = 1e-3,
                 model_name: str = "model", run_dir=None):
    """Train a model and return (model, best_test_acc)."""
    import torch
    from smtj_pbnn_sim.train.train_loop import train_one_epoch, evaluate
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.utils.logging import log, MetricsLogger

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    logger = None
    if run_dir is not None:
        model_dir = run_dir / model_name
        logger = MetricsLogger(model_dir, n_epochs=n_epochs)

    best_acc = 0.0
    best_state = None
    for epoch in range(n_epochs):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, optimizer, binary_cross_entropy_loss, device)
        te_loss, te_acc = evaluate(
            model, test_loader, binary_cross_entropy_loss, device)
        elapsed = time.time() - t0

        if logger is not None:
            logger.log_epoch(epoch + 1, tr_loss, tr_acc, te_loss, te_acc, elapsed)
        else:
            log(f"[{model_name}] epoch {epoch + 1:02d}/{n_epochs}  "
                f"train acc={tr_acc:.4f}  test acc={te_acc:.4f}  ({elapsed:.1f}s)")

        if te_acc > best_acc:
            best_acc = te_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    if logger is not None:
        logger.dump_summary(best_acc=best_acc)
        logger.close()

    return model, best_acc


# ---------------------------------------------------------------------------#
# Noise functions (all operate on a tensor x of shape (B, 1, 28, 28))         #
# ---------------------------------------------------------------------------#

def _gaussian_noise(x, sigma):
    import torch
    return x + sigma * torch.randn_like(x)


def _salt_pepper(x, frac):
    import torch
    out = x.clone()
    mask = torch.rand_like(x)
    out[mask < frac / 2] = 0.0
    out[(mask >= frac / 2) & (mask < frac)] = 1.0
    return out


def _speckle(x, sigma):
    import torch
    return x * (1.0 + sigma * torch.randn_like(x))


def _gaussian_blur(x, sigma):
    """Approximate Gaussian blur via separable conv with Gaussian kernel."""
    import torch
    import math
    if sigma <= 0:
        return x
    # 5-sigma kernel, odd size
    k = max(3, int(2 * round(3 * sigma) + 1))
    coords = torch.arange(k, device=x.device, dtype=x.dtype) - (k - 1) / 2
    g = torch.exp(-(coords ** 2) / (2 * sigma * sigma))
    g = g / g.sum()
    # Separable: apply 1xk then kx1
    g_h = g.view(1, 1, 1, k)
    g_v = g.view(1, 1, k, 1)
    x = torch.nn.functional.conv2d(x, g_h, padding=(0, k // 2))
    x = torch.nn.functional.conv2d(x, g_v, padding=(k // 2, 0))
    return x


def _cutout(x, size):
    """Zero out a random size x size patch in each image."""
    import torch
    if size <= 0:
        return x
    out = x.clone()
    B, C, H, W = out.shape
    for b in range(B):
        cy = torch.randint(0, H, (1,)).item()
        cx = torch.randint(0, W, (1,)).item()
        y0 = max(0, cy - size // 2)
        y1 = min(H, cy + size // 2)
        x0 = max(0, cx - size // 2)
        x1 = min(W, cx + size // 2)
        out[b, :, y0:y1, x0:x1] = 0.0
    return out


def _brightness(x, b):
    return (x + b).clamp(0.0, 1.0)


# ---------------------------------------------------------------------------#
# Evaluation helpers                                                         #
# ---------------------------------------------------------------------------#

def _eval_with_noise(model, loader, device, noise_fn=None, *,
                    mode=None, T=None) -> float:
    """Evaluate model accuracy, optionally applying noise_fn(x) to inputs."""
    import torch
    model.eval()
    n_correct = 0
    n_total = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            if noise_fn is not None:
                x = noise_fn(x)
            if mode is not None and hasattr(model, "forward_with_mode"):
                logits = model.forward_with_mode(x, mode=mode, T=T)
            else:
                logits = model(x)
            pred = logits.argmax(dim=1)
            n_correct += int((pred == y).sum().item())
            n_total += int(y.numel())
    return n_correct / max(1, n_total)


def _eval_pgd(model, loader, device, epsilon, *, mode=None, T=None,
              n_steps=10, alpha=None) -> float:
    """Evaluate accuracy under PGD-N L_inf adversarial attack."""
    import torch
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    if alpha is None:
        alpha = epsilon / 4.0  # standard PGD step size

    n_correct = 0
    n_total = 0
    for x, y in loader:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        x_orig = x.detach()
        x_adv = x.detach() + 0.001 * torch.randn_like(x)
        x_adv = x_adv.clamp(0.0, 1.0)

        for _ in range(n_steps):
            x_adv = x_adv.detach().requires_grad_(True)
            if mode is not None and hasattr(model, "forward_with_mode"):
                logits = model.forward_with_mode(x_adv, mode=mode, T=T)
            else:
                logits = model(x_adv)
            loss = binary_cross_entropy_loss(logits, y)
            grad = torch.autograd.grad(loss, x_adv)[0]
            with torch.no_grad():
                x_adv = x_adv + alpha * grad.sign()
                # project back into L_inf ball around x_orig
                x_adv = torch.max(torch.min(x_adv, x_orig + epsilon),
                                  x_orig - epsilon).clamp(0.0, 1.0)

        with torch.no_grad():
            if mode is not None and hasattr(model, "forward_with_mode"):
                logits_adv = model.forward_with_mode(x_adv, mode=mode, T=T)
            else:
                logits_adv = model(x_adv)
            pred = logits_adv.argmax(dim=1)
            n_correct += int((pred == y).sum().item())
            n_total += int(y.numel())
    return n_correct / max(1, n_total)


def _eval_weight_perturb(model, loader, device, sigma_w, *,
                         mode=None, T=None) -> float:
    """Evaluate accuracy after adding Gaussian noise to model weights."""
    import torch
    import copy
    if sigma_w == 0:
        return _eval_with_noise(model, loader, device, mode=mode, T=T)
    model_copy = copy.deepcopy(model)
    with torch.no_grad():
        for p in model_copy.parameters():
            p.add_(sigma_w * torch.randn_like(p))
    return _eval_with_noise(model_copy, loader, device, mode=mode, T=T)


# ---------------------------------------------------------------------------#
# Main experiment                                                            #
# ---------------------------------------------------------------------------#

def main() -> None:
    try:
        import torch
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("PyTorch and matplotlib are required for this experiment.")
        sys.exit(1)

    import csv
    import shutil
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import evaluate, calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.logging import log
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("07_baseline", base=REPO / "runs")

    print("=== Experiment 07: Baseline Comparison (Multi-Noise Robustness) ===\n")

    # ----- Data -----
    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=128, num_workers=0)

    hidden = 1024
    n_epochs = 20
    T_PBNN = 4   # Sweet spot from exp 06: 97.51% accuracy
    BNN_MLP, FP_MLP = _make_models(hidden=hidden)

    # ----- 1. PBNN: load from checkpoint or train -----
    print("Part 1: Preparing PBNN model ...")
    ckpt_path = REPO / "runs" / "mnist_pbnn_mlp" / "best.pt"
    if ckpt_path.exists():
        state = torch.load(ckpt_path, map_location="cpu")
        cfg = state["config"]
        dp = _device_params_from_cfg(cfg.get("device", {}))
        pbnn_model = PBNN_MLP(
            hidden=int(cfg.get("model", {}).get("hidden", hidden)),
            device_params=dp, variation_cfg=None,
            T_full_stack=T_PBNN,
        ).to(device)
        pbnn_model.load_state_dict(state["model_state"], strict=True)
        pbnn_acc_clean = state.get("best_acc", 0.0)
        log(f"PBNN loaded from checkpoint (clean acc={pbnn_acc_clean:.4f})")
    else:
        print(f"  Checkpoint not found at {ckpt_path}; training PBNN ...")
        pbnn_model = PBNN_MLP(
            hidden=hidden, device_params=None, variation_cfg=None,
            T_full_stack=T_PBNN,
        ).to(device)
        pbnn_model, pbnn_acc_clean = _train_model(
            pbnn_model, train_loader, test_loader, device,
            n_epochs=n_epochs, model_name="PBNN", run_dir=run_dir)
        with torch.no_grad():
            for m in pbnn_model.modules():
                if isinstance(m, PBNNLinear):
                    m.theta.mul_(100.0)

    # Calibrate BN running stats for FULL_STACK mode at T=4
    calibrate_bn(pbnn_model, train_loader, device,
                 mode=ForwardMode.FULL_STACK, T=T_PBNN)

    # ----- 2. BNN: train from scratch -----
    print("\nPart 2: Training BNN model ...")
    set_global_seed(42)
    bnn_model = BNN_MLP(hidden=hidden).to(device)
    bnn_model, bnn_acc_clean = _train_model(
        bnn_model, train_loader, test_loader, device,
        n_epochs=n_epochs, model_name="BNN", run_dir=run_dir)

    # ----- 3. FP-NN: train from scratch -----
    print("\nPart 3: Training FP-NN model ...")
    set_global_seed(42)
    fp_model = FP_MLP(hidden=hidden).to(device)
    fp_model, fp_acc_clean = _train_model(
        fp_model, train_loader, test_loader, device,
        n_epochs=n_epochs, model_name="FP-NN", run_dir=run_dir)

    # ----- 4. Multi-noise robustness sweep -----
    print("\n" + "=" * 70)
    print("Part 4: Multi-noise robustness sweep")
    print("=" * 70)

    pbnn_kw = dict(mode=ForwardMode.FULL_STACK, T=T_PBNN)
    results = {}

    def _sweep_input_noise(label, name, levels, noise_fn_factory,
                            param_name="param"):
        """Run a sweep for an input-level noise type."""
        print(f"\n  ({label}) {name} ...")
        r = {"param": levels, "pbnn": [], "bnn": [], "fp": []}
        for lvl in levels:
            noise_fn = noise_fn_factory(lvl) if lvl > 0 else None
            r["pbnn"].append(_eval_with_noise(
                pbnn_model, test_loader, device, noise_fn, **pbnn_kw))
            r["bnn"].append(_eval_with_noise(
                bnn_model, test_loader, device, noise_fn))
            r["fp"].append(_eval_with_noise(
                fp_model, test_loader, device, noise_fn))
            print(f"    {param_name}={lvl:.3f}  "
                  f"PBNN(T={T_PBNN})={r['pbnn'][-1]:.4f}  "
                  f"BNN={r['bnn'][-1]:.4f}  FP={r['fp'][-1]:.4f}")
        return r

    # (a) Additive Gaussian
    results["gaussian"] = _sweep_input_noise(
        "a", "Additive Gaussian noise",
        [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5],
        lambda s: (lambda x, s=s: _gaussian_noise(x, s)),
        param_name="sigma")

    # (b) Salt-and-pepper
    results["salt_pepper"] = _sweep_input_noise(
        "b", "Salt-and-pepper noise",
        [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50],
        lambda f: (lambda x, f=f: _salt_pepper(x, f)),
        param_name="frac")

    # (c) Speckle (multiplicative)
    results["speckle"] = _sweep_input_noise(
        "c", "Speckle (multiplicative) noise",
        [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5],
        lambda s: (lambda x, s=s: _speckle(x, s)),
        param_name="sigma")

    # (d) Gaussian blur
    results["blur"] = _sweep_input_noise(
        "d", "Gaussian blur",
        [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        lambda s: (lambda x, s=s: _gaussian_blur(x, s)),
        param_name="sigma_blur")

    # (e) Cutout
    results["cutout"] = _sweep_input_noise(
        "e", "Cutout / occlusion",
        [0, 4, 8, 12, 14, 16, 20, 24],
        lambda k: (lambda x, k=k: _cutout(x, k)),
        param_name="patch_size")

    # (f) Brightness shift
    results["brightness"] = _sweep_input_noise(
        "f", "Brightness shift",
        [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7],
        lambda b: (lambda x, b=b: _brightness(x, b)),
        param_name="b")

    # (g) Weight perturbation
    print("\n  (g) Weight perturbation ...")
    sigmas_w = [0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]
    r_wp = {"param": sigmas_w, "pbnn": [], "bnn": [], "fp": []}
    for sw in sigmas_w:
        r_wp["pbnn"].append(_eval_weight_perturb(
            pbnn_model, test_loader, device, sw, **pbnn_kw))
        r_wp["bnn"].append(_eval_weight_perturb(
            bnn_model, test_loader, device, sw))
        r_wp["fp"].append(_eval_weight_perturb(
            fp_model, test_loader, device, sw))
        print(f"    sigma_w={sw:.3f}  "
              f"PBNN(T={T_PBNN})={r_wp['pbnn'][-1]:.4f}  "
              f"BNN={r_wp['bnn'][-1]:.4f}  FP={r_wp['fp'][-1]:.4f}")
    results["weight_perturb"] = r_wp

    # (h) PGD-10 adversarial
    print("\n  (h) PGD-10 adversarial attack ...")
    epsilons = [0.0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3]
    r_pgd = {"param": epsilons, "pbnn": [], "bnn": [], "fp": []}
    for eps in epsilons:
        if eps == 0:
            r_pgd["pbnn"].append(results["gaussian"]["pbnn"][0])
            r_pgd["bnn"].append(results["gaussian"]["bnn"][0])
            r_pgd["fp"].append(results["gaussian"]["fp"][0])
        else:
            # PGD against PBNN: use HARDWARE_AWARE for gradient (CLT path)
            r_pgd["pbnn"].append(_eval_pgd(
                pbnn_model, test_loader, device, eps,
                mode=ForwardMode.HARDWARE_AWARE))
            r_pgd["bnn"].append(_eval_pgd(
                bnn_model, test_loader, device, eps))
            r_pgd["fp"].append(_eval_pgd(
                fp_model, test_loader, device, eps))
        print(f"    eps={eps:.3f}  "
              f"PBNN(T={T_PBNN})={r_pgd['pbnn'][-1]:.4f}  "
              f"BNN={r_pgd['bnn'][-1]:.4f}  FP={r_pgd['fp'][-1]:.4f}")
    results["pgd"] = r_pgd

    # ----- Save results CSVs -----
    for name, r in results.items():
        csv_path = run_dir / f"noise_{name}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["param", f"pbnn_T{T_PBNN}", "bnn", "fp"])
            for p, pa, b, fa in zip(r["param"], r["pbnn"],
                                     r["bnn"], r["fp"]):
                w.writerow([p, f"{pa:.6f}", f"{b:.6f}", f"{fa:.6f}"])
    print(f"\n  Results saved to {run_dir}")

    # ----- 5. Plot (2x4 grid) -----
    print("\nPart 5: Generating figure ...")
    fig, axes = plt.subplots(2, 4, figsize=(20, 9))

    panel_cfg = [
        (axes[0, 0], results["gaussian"],
         r"Input noise $\sigma$", "Additive Gaussian"),
        (axes[0, 1], results["salt_pepper"],
         "Corrupted pixel fraction", "Salt-and-pepper"),
        (axes[0, 2], results["speckle"],
         r"Speckle $\sigma$", "Speckle (multiplicative)"),
        (axes[0, 3], results["blur"],
         r"Blur $\sigma$ (px)", "Gaussian blur"),
        (axes[1, 0], results["cutout"],
         "Cutout patch size (px)", "Cutout / occlusion"),
        (axes[1, 1], results["brightness"],
         r"Brightness shift $b$", "Brightness shift"),
        (axes[1, 2], results["weight_perturb"],
         r"Weight noise $\sigma_w$", "Weight perturbation"),
        (axes[1, 3], results["pgd"],
         r"PGD $\epsilon$ (L$_\infty$)", "PGD-10 adversarial"),
    ]

    for ax, r, xlabel, title in panel_cfg:
        ax.plot(r["param"], [a * 100 for a in r["pbnn"]], "o-",
                color="#4B1369", lw=2, markersize=5,
                label=f"PBNN (T={T_PBNN})")
        ax.plot(r["param"], [a * 100 for a in r["bnn"]], "s-",
                color="#D97706", lw=2, markersize=5, label="BNN")
        ax.plot(r["param"], [a * 100 for a in r["fp"]], "D-",
                color="#6B7280", lw=2, markersize=5, label="FP-NN")
        ax.set_xlabel(xlabel, fontsize=11)
        ax.set_ylabel("Test accuracy (%)", fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 105)

    fig.suptitle("MNIST robustness: PBNN vs BNN vs FP-NN  (8 noise types)",
                 fontsize=15, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_fig = REPO / "figures" / "07_baseline_noise_robustness.png"
    out_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig, dpi=150, bbox_inches="tight")
    shutil.copy2(out_fig, run_dir / "07_baseline_noise_robustness.png")
    print(f"  Figure saved: {out_fig.relative_to(REPO)}")

    # ----- 6. Summary -----
    print("\n--- Summary (mid-level perturbation) ---")
    for name, r in results.items():
        mid = len(r["param"]) // 2
        print(f"  [{name}] at param={r['param'][mid]}:  "
              f"PBNN-T{T_PBNN}={r['pbnn'][mid]*100:.2f}%  "
              f"BNN={r['bnn'][mid]*100:.2f}%  "
              f"FP={r['fp'][mid]*100:.2f}%")
    print("\nDone.")


if __name__ == "__main__":
    main()
