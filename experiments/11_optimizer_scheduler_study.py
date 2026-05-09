"""11 -- Optimizer & learning-rate scheduler study on MNIST PBNN.

Investigates how the choice of optimizer and learning-rate scheduler
affects PBNN-MLP training on MNIST.  All runs share the same model
topology, dataset, batch size, and number of epochs; only the
optimizer (Part A) or scheduler (Part B) varies.

Part A: Optimizer comparison
----------------------------

Eight optimizers, each given the LR commonly recommended in its
original paper (no further per-optimizer tuning):

  Classical:    SGD (mom=0.9), Adam, AdamW, RMSprop, Adamax
  Recent:       NAdam, RAdam, Lion (Chen et al., 2023)

Part B: Learning-rate scheduler comparison
------------------------------------------

Five LR schedules, all on top of Adam (lr=1e-3):

  - constant     (no schedule, baseline)
  - StepLR       (step=5 epochs, gamma=0.5)
  - CosineAnneal (T_max=n_epochs)
  - OneCycleLR   (max_lr=5e-3, pct_start=0.3)
  - ExponentialLR(gamma=0.95)

Outputs:
  figures/11a_optimizers.png      accuracy + loss vs epoch
  figures/11b_schedulers.png      accuracy + loss + lr vs epoch
  runs/11_optim_<ts>/<name>_history.csv

Run from the repo root:

    python experiments/11_optimizer_scheduler_study.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Lion optimizer (Chen et al., 2023, arXiv 2302.06675)                       #
# ---------------------------------------------------------------------------#

def _lion_class():
    """Returns a Lion optimizer class (lazy-import torch)."""
    import torch

    class Lion(torch.optim.Optimizer):
        """Lion: Evolved sign-momentum optimizer (Chen et al. 2023)."""

        def __init__(self, params, lr=1e-4, betas=(0.9, 0.99),
                     weight_decay=0.0):
            if lr <= 0.0:
                raise ValueError(f"Invalid learning rate: {lr}")
            defaults = dict(lr=lr, betas=betas, weight_decay=weight_decay)
            super().__init__(params, defaults)

        @torch.no_grad()
        def step(self, closure=None):
            loss = None
            if closure is not None:
                with torch.enable_grad():
                    loss = closure()

            for group in self.param_groups:
                lr = group["lr"]
                beta1, beta2 = group["betas"]
                wd = group["weight_decay"]

                for p in group["params"]:
                    if p.grad is None:
                        continue
                    grad = p.grad
                    state = self.state[p]
                    if len(state) == 0:
                        state["exp_avg"] = torch.zeros_like(p)
                    exp_avg = state["exp_avg"]

                    # Decoupled weight decay
                    if wd != 0.0:
                        p.mul_(1.0 - lr * wd)

                    # Update direction = sign(beta1 * m + (1 - beta1) * g)
                    update = exp_avg.mul(beta1).add(grad, alpha=1.0 - beta1)
                    p.add_(update.sign_(), alpha=-lr)

                    # Update momentum
                    exp_avg.mul_(beta2).add_(grad, alpha=1.0 - beta2)
            return loss

    return Lion


# ---------------------------------------------------------------------------#
# Generic training loop with optional scheduler                              #
# ---------------------------------------------------------------------------#

def _train_one_run(model_factory, optimizer_factory, scheduler_factory,
                   train_loader, test_loader, criterion, device,
                   n_epochs, label):
    """Train PBNN-MLP under a given optimizer + scheduler config.

    ``scheduler_factory(optimizer, n_batches, n_epochs)`` -> scheduler or None
    """
    import torch
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode

    set_seed = lambda: None  # caller pre-seeds
    model = model_factory().to(device)
    optimizer = optimizer_factory(model.parameters())
    scheduler = scheduler_factory(optimizer, len(train_loader), n_epochs)

    # OneCycleLR steps per batch; the rest step per epoch.
    per_batch = isinstance(
        scheduler,
        (torch.optim.lr_scheduler.OneCycleLR,)
    ) if scheduler is not None else False

    history = {
        "train_loss": [], "train_acc": [],
        "test_loss":  [], "test_acc":  [],
        "lr":         [], "epoch_s":   [],
    }

    for epoch in range(n_epochs):
        t0 = time.time()
        model.train()
        tr_loss_sum, tr_correct, n_seen = 0.0, 0, 0
        for x, y in train_loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            logits = model.forward_with_mode(
                x, mode=ForwardMode.HARDWARE_AWARE)
            loss = criterion(logits, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            if per_batch and scheduler is not None:
                scheduler.step()
            tr_loss_sum += float(loss.item()) * x.size(0)
            tr_correct += int((logits.argmax(1) == y).sum().item())
            n_seen += x.size(0)

        model.eval()
        te_loss_sum, te_correct, n_te = 0.0, 0, 0
        with torch.no_grad():
            for x, y in test_loader:
                x = x.to(device, non_blocking=True)
                y = y.to(device, non_blocking=True)
                logits = model.forward_with_mode(
                    x, mode=ForwardMode.HARDWARE_AWARE)
                loss = criterion(logits, y)
                te_loss_sum += float(loss.item()) * x.size(0)
                te_correct += int((logits.argmax(1) == y).sum().item())
                n_te += x.size(0)

        if scheduler is not None and not per_batch:
            scheduler.step()

        history["train_loss"].append(tr_loss_sum / max(1, n_seen))
        history["train_acc"].append(tr_correct / max(1, n_seen))
        history["test_loss"].append(te_loss_sum / max(1, n_te))
        history["test_acc"].append(te_correct / max(1, n_te))
        history["lr"].append(optimizer.param_groups[0]["lr"])
        history["epoch_s"].append(time.time() - t0)
        print(f"  [{label}] epoch {epoch + 1:02d}/{n_epochs}  "
              f"train acc={history['train_acc'][-1]:.4f}  "
              f"test acc={history['test_acc'][-1]:.4f}  "
              f"lr={history['lr'][-1]:.4g}  "
              f"({history['epoch_s'][-1]:.1f}s)")

    return history


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
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, DeviceLayerParams
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    Lion = _lion_class()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("11_optim", base=REPO / "runs")

    print("=== Experiment 11: Optimizer & LR-scheduler study ===\n")
    print(f"Device: {device}")
    print(f"Run dir: {run_dir}\n")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=128, num_workers=0)

    n_epochs = 15  # enough to show convergence behavior; ~9s/epoch on GPU
    hidden = 1024

    def model_factory():
        return PBNN_MLP(
            hidden=hidden, device_params=DeviceLayerParams(),
            variation_cfg=None, T_full_stack=8,
        )

    # ----- Part A: optimizer comparison -----
    print("=" * 70)
    print("Part A: Optimizer comparison (constant LR, no schedule)")
    print("=" * 70)

    optimizers = {
        "SGD-mom":  (lambda p: torch.optim.SGD(p, lr=1e-2, momentum=0.9),
                     "SGD with momentum (Polyak 1964)"),
        "Adam":     (lambda p: torch.optim.Adam(p, lr=1e-3),
                     "Adam (Kingma & Ba, 2014)"),
        "AdamW":    (lambda p: torch.optim.AdamW(p, lr=1e-3, weight_decay=1e-2),
                     "AdamW (Loshchilov & Hutter, 2017)"),
        "NAdam":    (lambda p: torch.optim.NAdam(p, lr=2e-3),
                     "NAdam (Dozat, 2016)"),
        "RAdam":    (lambda p: torch.optim.RAdam(p, lr=1e-3),
                     "RAdam (Liu et al., 2019)"),
        "Adamax":   (lambda p: torch.optim.Adamax(p, lr=2e-3),
                     "Adamax (Kingma & Ba, 2014)"),
        "RMSprop":  (lambda p: torch.optim.RMSprop(p, lr=1e-3),
                     "RMSprop (Tieleman & Hinton, 2012)"),
        "Lion":     (lambda p: Lion(p, lr=1e-4, weight_decay=1e-2),
                     "Lion (Chen et al., 2023)"),
    }

    histories_A = {}
    for name, (factory, desc) in optimizers.items():
        print(f"\n--- {name}: {desc} ---")
        set_global_seed(42)
        h = _train_one_run(
            model_factory=model_factory,
            optimizer_factory=factory,
            scheduler_factory=lambda opt, nb, ne: None,
            train_loader=train_loader, test_loader=test_loader,
            criterion=binary_cross_entropy_loss,
            device=device, n_epochs=n_epochs, label=name)
        histories_A[name] = h

        # save per-optimizer CSV
        with open(run_dir / f"optimizer_{name}.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["epoch", "train_loss", "train_acc",
                        "test_loss", "test_acc", "lr", "epoch_s"])
            for e in range(n_epochs):
                w.writerow([e + 1,
                            f"{h['train_loss'][e]:.6f}",
                            f"{h['train_acc'][e]:.6f}",
                            f"{h['test_loss'][e]:.6f}",
                            f"{h['test_acc'][e]:.6f}",
                            f"{h['lr'][e]:.6g}",
                            f"{h['epoch_s'][e]:.2f}"])

    # ----- Part B: scheduler comparison -----
    print("\n" + "=" * 70)
    print("Part B: LR scheduler comparison (Adam, lr=1e-3)")
    print("=" * 70)

    base_optim = lambda p: torch.optim.Adam(p, lr=1e-3)

    schedulers = {
        "constant":     (lambda opt, nb, ne: None,
                         "no schedule (baseline)"),
        "StepLR":       (lambda opt, nb, ne:
                         torch.optim.lr_scheduler.StepLR(
                             opt, step_size=5, gamma=0.5),
                         "step-decay every 5 epochs, gamma=0.5"),
        "CosineAnneal": (lambda opt, nb, ne:
                         torch.optim.lr_scheduler.CosineAnnealingLR(
                             opt, T_max=ne),
                         "cosine annealing (Loshchilov & Hutter 2017)"),
        "OneCycleLR":   (lambda opt, nb, ne:
                         torch.optim.lr_scheduler.OneCycleLR(
                             opt, max_lr=5e-3, total_steps=nb * ne,
                             pct_start=0.3, anneal_strategy="cos"),
                         "one-cycle policy (Smith 2018)"),
        "ExpLR-0.95":   (lambda opt, nb, ne:
                         torch.optim.lr_scheduler.ExponentialLR(
                             opt, gamma=0.95),
                         "exponential decay, gamma=0.95"),
    }

    histories_B = {}
    for name, (sch_factory, desc) in schedulers.items():
        print(f"\n--- Scheduler: {name}  ({desc}) ---")
        set_global_seed(42)
        h = _train_one_run(
            model_factory=model_factory,
            optimizer_factory=base_optim,
            scheduler_factory=sch_factory,
            train_loader=train_loader, test_loader=test_loader,
            criterion=binary_cross_entropy_loss,
            device=device, n_epochs=n_epochs, label=name)
        histories_B[name] = h

        with open(run_dir / f"scheduler_{name}.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["epoch", "train_loss", "train_acc",
                        "test_loss", "test_acc", "lr", "epoch_s"])
            for e in range(n_epochs):
                w.writerow([e + 1,
                            f"{h['train_loss'][e]:.6f}",
                            f"{h['train_acc'][e]:.6f}",
                            f"{h['test_loss'][e]:.6f}",
                            f"{h['test_acc'][e]:.6f}",
                            f"{h['lr'][e]:.6g}",
                            f"{h['epoch_s'][e]:.2f}"])

    # ----- Save summary -----
    summary_path = run_dir / "summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["experiment", "name", "best_test_acc",
                    "epoch_at_best", "final_test_acc",
                    "total_time_s"])
        for name, h in histories_A.items():
            best = max(h["test_acc"])
            best_e = int(h["test_acc"].index(best)) + 1
            w.writerow(["A_optimizer", name,
                        f"{best:.6f}", best_e,
                        f"{h['test_acc'][-1]:.6f}",
                        f"{sum(h['epoch_s']):.2f}"])
        for name, h in histories_B.items():
            best = max(h["test_acc"])
            best_e = int(h["test_acc"].index(best)) + 1
            w.writerow(["B_scheduler", name,
                        f"{best:.6f}", best_e,
                        f"{h['test_acc'][-1]:.6f}",
                        f"{sum(h['epoch_s']):.2f}"])
    print(f"\nSummary CSV saved: {summary_path}")

    # ----- Plot Part A: optimizer comparison -----
    print("\nGenerating figures ...")
    colors_A = ["#4B1369", "#6E2C91", "#8E54A8", "#D97706",
                "#0E8A6F", "#1D4E89", "#A82038", "#6B7280"]
    fig_a, axes_a = plt.subplots(1, 2, figsize=(14, 5))
    epochs = list(range(1, n_epochs + 1))
    for (name, h), color in zip(histories_A.items(), colors_A):
        axes_a[0].plot(epochs, [a * 100 for a in h["test_acc"]], "o-",
                        color=color, lw=1.7, markersize=4,
                        label=f"{name} (best {max(h['test_acc']) * 100:.2f}%)")
        axes_a[1].plot(epochs, h["train_loss"], "-",
                        color=color, lw=1.7, label=name)
    axes_a[0].set_xlabel("Epoch"); axes_a[0].set_ylabel("Test accuracy (%)")
    axes_a[0].set_title("Part A: Optimizer comparison — test accuracy")
    axes_a[0].grid(alpha=0.3); axes_a[0].legend(fontsize=8, loc="lower right")
    axes_a[0].set_ylim(80, 100)
    axes_a[1].set_xlabel("Epoch"); axes_a[1].set_ylabel("Train loss")
    axes_a[1].set_title("Part A: Optimizer comparison — train loss")
    axes_a[1].grid(alpha=0.3); axes_a[1].legend(fontsize=8)
    axes_a[1].set_yscale("log")
    fig_a.suptitle("MNIST PBNN-MLP — optimizer comparison (constant LR)",
                   fontsize=14, y=1.02)
    fig_a.tight_layout()
    out_a = REPO / "figures" / "11a_optimizers.png"
    out_a.parent.mkdir(parents=True, exist_ok=True)
    fig_a.savefig(out_a, dpi=150, bbox_inches="tight")
    shutil.copy2(out_a, run_dir / "11a_optimizers.png")
    print(f"  Figure A saved: {out_a.relative_to(REPO)}")

    # ----- Plot Part B: scheduler comparison -----
    colors_B = ["#6B7280", "#4B1369", "#D97706", "#0E8A6F", "#A82038"]
    fig_b, axes_b = plt.subplots(1, 3, figsize=(20, 5))
    for (name, h), color in zip(histories_B.items(), colors_B):
        axes_b[0].plot(epochs, [a * 100 for a in h["test_acc"]], "o-",
                        color=color, lw=1.7, markersize=4,
                        label=f"{name} (best {max(h['test_acc']) * 100:.2f}%)")
        axes_b[1].plot(epochs, h["train_loss"], "-",
                        color=color, lw=1.7, label=name)
        axes_b[2].plot(epochs, h["lr"], "o-",
                        color=color, lw=1.7, markersize=4, label=name)
    axes_b[0].set_xlabel("Epoch"); axes_b[0].set_ylabel("Test accuracy (%)")
    axes_b[0].set_title("Part B: Scheduler comparison — test accuracy")
    axes_b[0].grid(alpha=0.3); axes_b[0].legend(fontsize=9, loc="lower right")
    axes_b[0].set_ylim(90, 100)
    axes_b[1].set_xlabel("Epoch"); axes_b[1].set_ylabel("Train loss")
    axes_b[1].set_title("Part B: Scheduler comparison — train loss")
    axes_b[1].grid(alpha=0.3); axes_b[1].legend(fontsize=9)
    axes_b[1].set_yscale("log")
    axes_b[2].set_xlabel("Epoch"); axes_b[2].set_ylabel("Learning rate")
    axes_b[2].set_title("Part B: Scheduler comparison — LR trajectory")
    axes_b[2].grid(alpha=0.3); axes_b[2].legend(fontsize=9)
    axes_b[2].set_yscale("log")
    fig_b.suptitle("MNIST PBNN-MLP — LR scheduler comparison (Adam, lr=1e-3)",
                   fontsize=14, y=1.02)
    fig_b.tight_layout()
    out_b = REPO / "figures" / "11b_schedulers.png"
    fig_b.savefig(out_b, dpi=150, bbox_inches="tight")
    shutil.copy2(out_b, run_dir / "11b_schedulers.png")
    print(f"  Figure B saved: {out_b.relative_to(REPO)}")

    # ----- Print summary -----
    print("\n--- Optimizer summary (Part A) ---")
    print(f"{'Optimizer':12s}  {'best acc':>8}  {'final acc':>9}  "
          f"{'best ep':>7}  {'time (s)':>8}")
    for name, h in histories_A.items():
        best = max(h["test_acc"])
        best_e = h["test_acc"].index(best) + 1
        total = sum(h["epoch_s"])
        print(f"{name:12s}  {best * 100:>7.2f}%  {h['test_acc'][-1] * 100:>8.2f}%"
              f"  {best_e:>7}  {total:>8.1f}")

    print("\n--- Scheduler summary (Part B, Adam) ---")
    print(f"{'Scheduler':14s}  {'best acc':>8}  {'final acc':>9}  "
          f"{'best ep':>7}  {'time (s)':>8}")
    for name, h in histories_B.items():
        best = max(h["test_acc"])
        best_e = h["test_acc"].index(best) + 1
        total = sum(h["epoch_s"])
        print(f"{name:14s}  {best * 100:>7.2f}%  {h['test_acc'][-1] * 100:>8.2f}%"
              f"  {best_e:>7}  {total:>8.1f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
