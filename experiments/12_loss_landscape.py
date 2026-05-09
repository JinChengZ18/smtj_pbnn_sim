"""12 -- Loss-landscape visualization for optimizer dynamics.

Explains why optimizers from Experiment 11 reach different test
accuracies by mapping the local loss landscape around each optimum,
the per-epoch trajectory in a shared 2D PCA projection, and the
linear interpolation between optima.

Three figures:

  12a -- Local loss-landscape contours (Goff-Li-style, filter-normalized
         random-direction projection) around each optimizer's converged
         theta. Sharp vs flat minima visible at a glance.

  12b -- Per-epoch trajectory of every optimizer projected onto the
         first two principal components of all checkpoints. Overlaid
         loss contours show whether different optimizers converge into
         the same basin or distinct basins.

  12c -- Pairwise linear interpolation between optima: for each pair
         (theta_A, theta_B), evaluate loss along
         theta(alpha) = (1 - alpha) * theta_A + alpha * theta_B
         for alpha in [0, 1]. Smooth dips => same basin; central
         barriers => distinct basins.

Reference for the filter-normalized direction sampling:

    Li et al., Visualizing the Loss Landscape of Neural Nets,
    NeurIPS 2018.

Run from the repo root:

    python experiments/12_loss_landscape.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Helpers                                                                    #
# ---------------------------------------------------------------------------#

def _flatten_state_dict(sd):
    """Concatenate all torch.Tensor entries of a state_dict into one 1-D tensor.

    Skips variation buffers (V_th_field, V_T_field) which are device-side
    state, and any tensor with zero elements (lazily-initialised empty
    buffers).  Keeps weights, biases, and BatchNorm running stats —
    everything that contributes to the trained-model identity.
    """
    import torch
    parts = []
    keys = []
    for k, v in sd.items():
        if not isinstance(v, torch.Tensor):
            continue
        if not v.dtype.is_floating_point:
            continue
        if v.numel() == 0:
            continue
        # Skip per-cell variation fields (device state, not trainable)
        if k.endswith("V_th_field") or k.endswith("V_T_field"):
            continue
        parts.append(v.detach().reshape(-1).cpu())
        keys.append((k, v.shape))
    return torch.cat(parts), keys


def _unflatten(vec, keys):
    """Inverse of :_flatten_state_dict."""
    import torch
    sd = {}
    offset = 0
    for k, shape in keys:
        n = 1
        for s in shape:
            n *= s
        sd[k] = vec[offset:offset + n].view(*shape).clone()
        offset += n
    return sd


def _filter_normalized_direction(theta_keys, theta_star_dict, generator):
    """Random direction normalized per-tensor to match theta_star magnitude.

    For each weight tensor in theta_star, sample a Gaussian direction
    with the same shape, then rescale to have the same Frobenius norm
    as the original tensor.  This is the standard "filter normalization"
    of Li et al. 2018 that makes loss-landscape plots scale-invariant
    across architectures.
    """
    import torch
    out = {}
    for k, shape in theta_keys:
        d = torch.randn(*shape, generator=generator, device="cpu")
        ref_norm = theta_star_dict[k].detach().norm().item()
        d_norm = d.norm().item()
        if d_norm > 1e-12:
            d = d * (ref_norm / d_norm)
        out[k] = d
    return out


def _set_weights(model, sd):
    """Load a state_dict-like mapping of floating-point tensors into model."""
    import torch
    msd = model.state_dict()
    for k, v in sd.items():
        if k in msd and isinstance(msd[k], torch.Tensor) \
                and msd[k].dtype.is_floating_point:
            msd[k].copy_(v.to(msd[k].device, msd[k].dtype))


def _eval_loss(model, x, y, criterion):
    import torch
    model.eval()
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    with torch.no_grad():
        logits = model.forward_with_mode(x, mode=ForwardMode.HARDWARE_AWARE)
        return float(criterion(logits, y).item())


# ---------------------------------------------------------------------------#
# Lion (re-used from experiment 11)                                          #
# ---------------------------------------------------------------------------#

def _lion_class():
    import torch
    class Lion(torch.optim.Optimizer):
        def __init__(self, params, lr=1e-4, betas=(0.9, 0.99),
                     weight_decay=0.0):
            super().__init__(params,
                             dict(lr=lr, betas=betas, weight_decay=weight_decay))
        @torch.no_grad()
        def step(self, closure=None):
            loss = closure() if closure else None
            for g in self.param_groups:
                lr, (b1, b2), wd = g["lr"], g["betas"], g["weight_decay"]
                for p in g["params"]:
                    if p.grad is None: continue
                    s = self.state[p]
                    if not s: s["exp_avg"] = torch.zeros_like(p)
                    m = s["exp_avg"]
                    if wd: p.mul_(1.0 - lr * wd)
                    upd = m.mul(b1).add(p.grad, alpha=1.0 - b1).sign_()
                    p.add_(upd, alpha=-lr)
                    m.mul_(b2).add_(p.grad, alpha=1.0 - b2)
            return loss
    return Lion


# ---------------------------------------------------------------------------#
# Train + checkpoint                                                         #
# ---------------------------------------------------------------------------#

def _train_and_checkpoint(model_factory, opt_factory, train_loader,
                           test_loader, criterion, device, n_epochs, label):
    import torch
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode

    model = model_factory().to(device)
    optimizer = opt_factory(model.parameters())
    checkpoints = []  # one per epoch, plus initial
    # Save initial weights
    checkpoints.append({k: v.detach().clone().cpu()
                        for k, v in model.state_dict().items()})

    for epoch in range(n_epochs):
        t0 = time.time()
        model.train()
        for x, y in train_loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            logits = model.forward_with_mode(x, mode=ForwardMode.HARDWARE_AWARE)
            loss = criterion(logits, y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        # eval
        model.eval()
        n_correct = n_total = 0
        with torch.no_grad():
            for x, y in test_loader:
                x = x.to(device, non_blocking=True)
                y = y.to(device, non_blocking=True)
                logits = model.forward_with_mode(
                    x, mode=ForwardMode.HARDWARE_AWARE)
                n_correct += int((logits.argmax(1) == y).sum().item())
                n_total += int(y.numel())
        acc = n_correct / max(1, n_total)
        elapsed = time.time() - t0
        print(f"  [{label}] epoch {epoch + 1:02d}/{n_epochs}  "
              f"test acc={acc:.4f}  ({elapsed:.1f}s)")
        checkpoints.append({k: v.detach().clone().cpu()
                            for k, v in model.state_dict().items()})
    return model, checkpoints


# ---------------------------------------------------------------------------#
# Main                                                                       #
# ---------------------------------------------------------------------------#

def main() -> None:
    try:
        import torch
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("PyTorch + matplotlib + numpy required.")
        sys.exit(1)

    import csv
    import shutil
    from itertools import combinations
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, DeviceLayerParams
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    Lion = _lion_class()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("12_landscape", base=REPO / "runs").resolve()
    # Re-create just in case the FS state was lost in a long-running session
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== Experiment 12: Loss-landscape & optimizer dynamics ===\n")
    print(f"Device: {device}")
    print(f"Run dir: {run_dir}\n")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=128, num_workers=0)

    # Use a small fixed eval batch for fast loss queries
    eval_x, eval_y = [], []
    with torch.no_grad():
        for x, y in test_loader:
            eval_x.append(x); eval_y.append(y)
            if sum(t.size(0) for t in eval_x) >= 1024:
                break
    eval_x = torch.cat(eval_x, dim=0)[:1024].to(device)
    eval_y = torch.cat(eval_y, dim=0)[:1024].to(device)

    n_epochs = 8   # enough for visible divergence in landscape; keep runtime ~7 min
    hidden = 512   # smaller than exp 05 to keep landscape eval fast

    def model_factory():
        return PBNN_MLP(
            hidden=hidden, device_params=DeviceLayerParams(),
            variation_cfg=None, T_full_stack=8,
        )

    optimizers = {
        "SGD-mom": (lambda p: torch.optim.SGD(p, lr=1e-2, momentum=0.9),
                    "Polyak 1964"),
        "Adam":    (lambda p: torch.optim.Adam(p, lr=1e-3),
                    "Kingma & Ba 2014"),
        "Lion":    (lambda p: Lion(p, lr=1e-4, weight_decay=1e-2),
                    "Chen et al. 2023"),
    }

    # ----- Train each optimizer; save per-epoch state_dicts -----
    print("=" * 65)
    print(f"Part 1: Train {len(optimizers)} optimizers, {n_epochs} epochs each")
    print("=" * 65)
    all_checkpoints = {}
    final_models = {}
    for name, (factory, _) in optimizers.items():
        print(f"\n--- {name} ---")
        set_global_seed(42)  # same init for all
        model, checkpoints = _train_and_checkpoint(
            model_factory=model_factory,
            opt_factory=factory,
            train_loader=train_loader, test_loader=test_loader,
            criterion=binary_cross_entropy_loss,
            device=device, n_epochs=n_epochs, label=name)
        all_checkpoints[name] = checkpoints  # list of state_dicts (cpu)
        final_models[name] = model

    # ----- 12a: per-optimizer local landscape contour -----
    print("\n" + "=" * 65)
    print("Part 12a: Local loss-landscape contours")
    print("=" * 65)
    GRID_N = 13                  # 13 x 13 grid (169 evals per opt)
    SPAN = 0.6                   # alpha, beta in [-SPAN, +SPAN]
    alphas = np.linspace(-SPAN, SPAN, GRID_N)
    betas = np.linspace(-SPAN, SPAN, GRID_N)

    landscape_data = {}  # name -> (alphas, betas, loss_grid)
    for name in optimizers:
        print(f"\n  Computing landscape for {name} ({GRID_N}x{GRID_N} grid) ...")
        # Get final theta and decompose
        sd_star = all_checkpoints[name][-1]
        theta_star_vec, keys = _flatten_state_dict(sd_star)
        theta_star_dict = {k: sd_star[k] for k, _ in keys}

        # Two random orthogonal directions, filter-normalized
        gen = torch.Generator().manual_seed(42)
        d1_dict = _filter_normalized_direction(keys, theta_star_dict, gen)
        d2_dict = _filter_normalized_direction(keys, theta_star_dict, gen)

        # Use the same model (from training) for fast weight swapping
        model = final_models[name]

        # Save current weights to restore later
        original_sd = {k: v.detach().clone() for k, v in model.state_dict().items()}

        loss_grid = np.zeros((GRID_N, GRID_N), dtype=np.float32)
        t_start = time.time()
        for i, a in enumerate(alphas):
            for j, b in enumerate(betas):
                offset_sd = {}
                for k, _ in keys:
                    offset_sd[k] = (theta_star_dict[k]
                                     + a * d1_dict[k]
                                     + b * d2_dict[k])
                _set_weights(model, offset_sd)
                loss_grid[i, j] = _eval_loss(
                    model, eval_x, eval_y, binary_cross_entropy_loss)
            if (i + 1) % 3 == 0:
                print(f"    row {i + 1}/{GRID_N}  "
                      f"({time.time() - t_start:.1f}s)")
        # Restore
        _set_weights(model, original_sd)
        landscape_data[name] = (alphas.copy(), betas.copy(), loss_grid)
        # Save CSV
        run_dir.mkdir(parents=True, exist_ok=True)  # defensive
        with open(run_dir / f"landscape_{name}.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["alpha", "beta", "loss"])
            for i, a in enumerate(alphas):
                for j, b in enumerate(betas):
                    w.writerow([f"{a:.4f}", f"{b:.4f}",
                                f"{loss_grid[i, j]:.6f}"])

    # ----- 12b: PCA trajectory -----
    print("\n" + "=" * 65)
    print("Part 12b: PCA trajectory of all optimizers")
    print("=" * 65)
    # Stack all (n_opt * (n_epochs+1)) checkpoints into a big matrix
    all_vecs = []
    labels = []  # (opt_name, epoch_index)
    for name, ckpts in all_checkpoints.items():
        for e_idx, ckpt in enumerate(ckpts):
            v, _ = _flatten_state_dict(ckpt)
            all_vecs.append(v.numpy())
            labels.append((name, e_idx))
    M = np.stack(all_vecs, axis=0)  # (N, D)
    M_centered = M - M.mean(axis=0, keepdims=True)
    # SVD: take first 2 PCs
    U, S, Vt = np.linalg.svd(M_centered, full_matrices=False)
    pcs = U[:, :2] * S[:2]  # (N, 2)
    print(f"  PCA: {M.shape[0]} checkpoints, {M.shape[1]:,} weights, "
          f"PC1 / PC2 explained variance = "
          f"{S[0]**2 / (S**2).sum():.3f} / {S[1]**2 / (S**2).sum():.3f}")

    # ----- 12c: pairwise linear interpolation between optima -----
    print("\n" + "=" * 65)
    print("Part 12c: Pairwise interpolation between optima")
    print("=" * 65)
    INTERP_STEPS = 21
    alphas_interp = np.linspace(0.0, 1.0, INTERP_STEPS)
    pairwise = {}  # ("A","B") -> [losses for each alpha]

    final_states = {name: all_checkpoints[name][-1] for name in optimizers}
    # Use the Adam-trained model as scratch for evaluation
    scratch_model = final_models["Adam"]
    keys = _flatten_state_dict(final_states["Adam"])[1]

    for nA, nB in combinations(optimizers.keys(), 2):
        sd_A = final_states[nA]
        sd_B = final_states[nB]
        losses = []
        for a in alphas_interp:
            mixed_sd = {}
            for k, _ in keys:
                mixed_sd[k] = (1.0 - a) * sd_A[k] + a * sd_B[k]
            _set_weights(scratch_model, mixed_sd)
            losses.append(_eval_loss(
                scratch_model, eval_x, eval_y, binary_cross_entropy_loss))
        pairwise[(nA, nB)] = losses
        print(f"  {nA} -> {nB}: "
              f"L(0)={losses[0]:.4f}  L(0.5)={losses[INTERP_STEPS // 2]:.4f}  "
              f"L(1)={losses[-1]:.4f}  "
              f"max-mid-loss={max(losses):.4f}")

    # Save interpolation CSV
    with open(run_dir / "pairwise_interp.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "alpha", "loss"])
        for (nA, nB), losses in pairwise.items():
            for a, l in zip(alphas_interp, losses):
                w.writerow([f"{nA}->{nB}", f"{a:.4f}", f"{l:.6f}"])

    # ===== Plot 12a =====
    print("\nGenerating figures ...")
    fig_a, axes_a = plt.subplots(1, len(optimizers),
                                  figsize=(5 * len(optimizers), 5))
    if len(optimizers) == 1:
        axes_a = [axes_a]
    for ax, name in zip(axes_a, optimizers):
        a_arr, b_arr, grid = landscape_data[name]
        # Use log scale for clearer "sharpness" view
        cs = ax.contourf(b_arr, a_arr, grid, levels=20, cmap="viridis")
        ax.contour(b_arr, a_arr, grid, levels=10,
                   colors="black", linewidths=0.5, alpha=0.6)
        ax.scatter([0], [0], marker="*", s=200,
                   color="white", edgecolor="black", zorder=5,
                   label=fr"$\theta^*$  L={grid[GRID_N // 2, GRID_N // 2]:.3f}")
        ax.set_xlabel(r"$\beta$ (filter-normalized)")
        ax.set_ylabel(r"$\alpha$ (filter-normalized)")
        ax.set_title(f"{name}  L_min={grid.min():.3f}  L_max={grid.max():.3f}")
        ax.legend(loc="upper right", fontsize=9)
        plt.colorbar(cs, ax=ax, label="test loss")
    fig_a.suptitle("12a: Local loss-landscape around each optimum  "
                    "(filter-normalized 2D random projection, Li et al. 2018)",
                    fontsize=14, y=1.02)
    fig_a.tight_layout()
    out_a = REPO / "figures" / "12a_landscape_contours.png"
    out_a.parent.mkdir(parents=True, exist_ok=True)
    fig_a.savefig(out_a, dpi=150, bbox_inches="tight")
    shutil.copy2(out_a, run_dir / "12a_landscape_contours.png")
    print(f"  Figure 12a saved: {out_a.relative_to(REPO)}")

    # ===== Plot 12b =====
    fig_b, ax_b = plt.subplots(figsize=(9, 7))
    colors = {"SGD-mom": "#A82038", "Adam": "#4B1369", "Lion": "#0E8A6F"}
    for name in optimizers:
        idxs = [i for i, (nm, e) in enumerate(labels) if nm == name]
        traj = pcs[idxs]
        # Trajectory
        ax_b.plot(traj[:, 0], traj[:, 1], "-", color=colors[name],
                  lw=1.5, alpha=0.6)
        ax_b.scatter(traj[:, 0], traj[:, 1], s=30, color=colors[name],
                     edgecolor="white", lw=0.5, zorder=3, label=None)
        # Highlight start and end
        ax_b.scatter(traj[0, 0], traj[0, 1], s=180, marker="o",
                     color=colors[name], edgecolor="black", lw=1.5,
                     zorder=4)
        ax_b.scatter(traj[-1, 0], traj[-1, 1], s=300, marker="*",
                     color=colors[name], edgecolor="black", lw=1.5,
                     zorder=5, label=f"{name} optimum")
    ax_b.set_xlabel("PC 1")
    ax_b.set_ylabel("PC 2")
    ax_b.set_title("12b: Optimizer trajectories in shared 2-D PCA projection  "
                    f"(circle = init, star = final;  PC1+PC2 = "
                    f"{(S[0]**2 + S[1]**2) / (S**2).sum() * 100:.1f}% variance)",
                    fontsize=12)
    ax_b.legend(loc="best")
    ax_b.grid(alpha=0.3)
    fig_b.tight_layout()
    out_b = REPO / "figures" / "12b_pca_trajectories.png"
    fig_b.savefig(out_b, dpi=150, bbox_inches="tight")
    shutil.copy2(out_b, run_dir / "12b_pca_trajectories.png")
    print(f"  Figure 12b saved: {out_b.relative_to(REPO)}")

    # ===== Plot 12c =====
    fig_c, ax_c = plt.subplots(figsize=(9, 5))
    for (nA, nB), losses in pairwise.items():
        ax_c.plot(alphas_interp, losses, "o-", lw=2,
                  markersize=5, label=f"{nA}  →  {nB}")
    ax_c.set_xlabel(r"interpolation $\alpha$:  $\theta(\alpha) = (1 - \alpha)\,\theta_A + \alpha\,\theta_B$")
    ax_c.set_ylabel("test loss")
    ax_c.set_title("12c: Pairwise linear interpolation between optima  "
                    "(barriers = distinct basins, monotone = co-aligned)",
                    fontsize=12)
    ax_c.legend(loc="best")
    ax_c.grid(alpha=0.3)
    fig_c.tight_layout()
    out_c = REPO / "figures" / "12c_optimum_interp.png"
    fig_c.savefig(out_c, dpi=150, bbox_inches="tight")
    shutil.copy2(out_c, run_dir / "12c_optimum_interp.png")
    print(f"  Figure 12c saved: {out_c.relative_to(REPO)}")

    # ===== Summary =====
    print("\n--- Summary ---")
    for name in optimizers:
        a, b, g = landscape_data[name]
        print(f"  {name:8s} landscape  Lmin={g.min():.4f}  "
              f"Lmax={g.max():.4f}  L(theta*)={g[GRID_N // 2, GRID_N // 2]:.4f}  "
              f"sharpness (max-min)={g.max() - g.min():.4f}")
    for (nA, nB), losses in pairwise.items():
        bump = max(losses) - max(losses[0], losses[-1])
        verdict = "co-aligned (no barrier)" if bump < 0.05 \
                  else f"barrier of height {bump:.3f}"
        print(f"  {nA} ↔ {nB}: {verdict}")
    print(f"\nRun directory: {run_dir}")
    print("Done.")


if __name__ == "__main__":
    main()
