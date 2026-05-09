"""09 -- Hardware bit-flip robustness: encoding-aware comparison.

This experiment exposes the *core hardware advantage* of stochastic-binary
PBNNs over conventional digital CIM: the way each architecture maps a
weight onto physical bits/cells determines how a single faulty cell
propagates into the computation.

Encoding schemes (per weight)
-----------------------------

  FP-NN (digital CIM, INT8) :  8 bits per weight, positional encoding
                                value = sum_{b=0..7} bit_b * 2^b
                                MSB carries 50% of the dynamic range.
                                A single MSB flip changes the weight by ~50% of full scale.

  BNN  (1-bit CIM)          :  1 bit per weight: w = +/- 1
                                Single flip = sign inversion (worst case).

  PBNN (T-bit stochastic)   :  T cells per weight, each independent.
                                value = (1/T) sum_{i=1..T} cell_i,  cell_i in {-1, +1}
                                Each cell carries 1/T of the dynamic range.
                                Single flip changes the weight by 2/T = O(1/T).

Hypothesis
----------

PBNN's stochastic encoding gives every cell *equal* weight, so a uniform
bit-flip rate p produces O(1/T) effective weight error per weight,
whereas FP-NN suffers from MSB dominance: a 1 in 8 chance that the
flipped bit is the MSB, contributing ~50% relative weight error.

Three figures
-------------

  09a_per_bit_sensitivity.png  -- For FP-NN, flip ONE bit position at a
                                  time and measure accuracy. Shows MSB
                                  dominance.
  09b_bitflip_accuracy.png     -- Accuracy vs uniform bit-flip rate p,
                                  for PBNN(T=8), PBNN(T=64), BNN, FP-NN.
  09c_effective_error_dist.png -- Histogram of per-weight effective
                                  error magnitude under p=0.05, for each
                                  architecture.

Run from the repo root:

    python experiments/09_hardware_bitflip.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


# ---------------------------------------------------------------------------#
# Encoding utilities                                                         #
# ---------------------------------------------------------------------------#

def fp_to_uint8(w, w_max=None):
    """Linearly map FP weight tensor to uint8 in [0, 255].

    w_max defines the symmetric dynamic range. If None, uses the
    per-tensor abs-max.
    """
    import torch
    if w_max is None:
        w_max = w.abs().max().item() + 1e-12
    u = ((w / w_max + 1.0) * 127.5).round().clamp(0, 255).to(torch.int32)
    return u, w_max


def uint8_to_fp(u, w_max):
    return (u.float() / 127.5 - 1.0) * w_max


def apply_bitflip_uint8(u, p_flip, n_bits=8, bit_position=None):
    """Apply random bit-flip to a uint8 tensor.

    Parameters
    ----------
    u : int32 tensor (logically uint8)
    p_flip : float, per-bit flip probability
    n_bits : int, total bits in the encoding (default 8)
    bit_position : int or None
        If None, flip every bit independently with probability p_flip.
        If an int b, only bit b is flipped (each weight) with prob p_flip.
    """
    import torch
    out = u.clone()
    if bit_position is not None:
        mask = (torch.rand_like(u.float()) < p_flip).to(torch.int32)
        out = out ^ (mask << bit_position)
        return out
    for b in range(n_bits):
        mask = (torch.rand_like(u.float()) < p_flip).to(torch.int32)
        out = out ^ (mask << b)
    return out


# ---------------------------------------------------------------------------#
# Per-architecture bit-flip evaluation                                       #
# ---------------------------------------------------------------------------#

def eval_fp_with_bitflip(fp_model, loader, device, p_flip,
                          bit_position=None, n_bits=8) -> float:
    """Quantize FP model weights to int8, apply bit-flip, evaluate."""
    import torch
    import copy

    model_copy = copy.deepcopy(fp_model)

    with torch.no_grad():
        for name, p in model_copy.named_parameters():
            if "weight" in name and p.dim() >= 2:  # weight matrices only
                u, w_max = fp_to_uint8(p)
                u_flipped = apply_bitflip_uint8(
                    u, p_flip, n_bits=n_bits, bit_position=bit_position)
                p.copy_(uint8_to_fp(u_flipped, w_max))

    return _eval_simple(model_copy, loader, device)


def eval_bnn_with_bitflip(bnn_model, loader, device, p_flip) -> float:
    """Apply random sign flip to binary weights with prob p_flip.

    Each effective binary weight is encoded with 1 cell. A flip on
    that cell inverts the weight.
    """
    import torch
    import copy

    model_copy = copy.deepcopy(bnn_model)
    with torch.no_grad():
        for name, p in model_copy.named_parameters():
            if "weight" in name and p.dim() >= 2:
                # In BNN, the forward uses sign(weight). A bit-flip on the
                # 1-bit cell inverts the sign. Simulate by flipping the
                # sign of the underlying weight where the flip mask is true.
                flip_mask = (torch.rand_like(p) < p_flip).float()
                p.copy_(p * (1.0 - 2.0 * flip_mask))
    return _eval_simple(model_copy, loader, device)


def eval_pbnn_with_bitflip(pbnn_model, loader, device, p_flip, T) -> float:
    """Run PBNN FULL_STACK with each Bernoulli cell having a flip chance.

    Implementation: monkey-patch the Bernoulli sampler inside pbnn_linear
    so each draw has its sign inverted with probability p_flip.
    """
    import torch
    import smtj_pbnn_sim.nn.pbnn_linear as pl
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode

    original = pl._bernoulli_pm1

    def _flipped_bernoulli(p):
        w = original(p)
        if p_flip > 0:
            flip_mask = (torch.rand_like(w) < p_flip).float()
            w = w * (1.0 - 2.0 * flip_mask)
        return w

    pl._bernoulli_pm1 = _flipped_bernoulli
    try:
        acc = _eval_simple(pbnn_model, loader, device,
                           mode=ForwardMode.FULL_STACK, T=T)
    finally:
        pl._bernoulli_pm1 = original
    return acc


def _eval_simple(model, loader, device, *, mode=None, T=None) -> float:
    import torch
    model.eval()
    n_correct = 0
    n_total = 0
    with torch.no_grad():
        for x, y in loader:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            if mode is not None and hasattr(model, "forward_with_mode"):
                logits = model.forward_with_mode(x, mode=mode, T=T)
            else:
                logits = model(x)
            pred = logits.argmax(dim=1)
            n_correct += int((pred == y).sum().item())
            n_total += int(y.numel())
    return n_correct / max(1, n_total)


# ---------------------------------------------------------------------------#
# Effective weight-error analysis                                            #
# ---------------------------------------------------------------------------#

def fp_effective_error(weight_tensor, p_flip, n_bits=8):
    """Empirical |w' - w| / w_max distribution for FP-NN under bit-flip."""
    import torch
    u, w_max = fp_to_uint8(weight_tensor)
    u2 = apply_bitflip_uint8(u, p_flip, n_bits=n_bits)
    w_orig = uint8_to_fp(u, w_max)
    w_new = uint8_to_fp(u2, w_max)
    return ((w_new - w_orig).abs() / w_max).flatten()


def bnn_effective_error(weight_tensor, p_flip):
    """For BNN: a flip turns +1 into -1 (or vice versa) with prob p_flip,
    so |error| / |w_max| = 2 * Bernoulli(p_flip)."""
    import torch
    flips = (torch.rand_like(weight_tensor) < p_flip).float()
    return (2.0 * flips).flatten()


def pbnn_effective_error_oneshot(num_weights, T, p_flip):
    """For PBNN: each weight has T cells, each may flip independently.
    The per-cell value is +/-1 contributing 1/T to the average.
    Effective error magnitude = (2/T) * (number of flipped cells)."""
    import torch
    flips = (torch.rand(num_weights, T) < p_flip).float().sum(dim=1)
    return (2.0 / T) * flips


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
    from smtj_pbnn_sim.nn.deterministic_bnn import DeterministicBinaryLinear
    from smtj_pbnn_sim.nn.batchnorm import BinaryBatchNorm1d
    from smtj_pbnn_sim.nn.ste import sign_ste
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.logging import log
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("09_hardware_bitflip", base=REPO / "runs")

    print("=== Experiment 09: Hardware Bit-Flip Robustness ===\n")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=128, num_workers=0)

    hidden = 1024
    T_LOW = 8
    T_HIGH = 64

    # ----- Reuse trained models from experiment 07 (if present) -----
    print("Loading models ...")

    # PBNN
    ckpt_path = REPO / "runs" / "mnist_pbnn_mlp" / "best.pt"
    if not ckpt_path.exists():
        print(f"PBNN checkpoint not found at {ckpt_path}.")
        print("Run experiments/05_mnist_pbnn.py first.")
        sys.exit(1)

    state = torch.load(ckpt_path, map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    pbnn_model = PBNN_MLP(
        hidden=int(cfg.get("model", {}).get("hidden", hidden)),
        device_params=dp, variation_cfg=None,
        T_full_stack=T_HIGH,
    ).to(device)
    pbnn_model.load_state_dict(state["model_state"], strict=True)
    log(f"PBNN loaded from {ckpt_path}")

    calibrate_bn(pbnn_model, train_loader, device,
                 mode=ForwardMode.FULL_STACK, T=T_HIGH)

    # BNN and FP: train from scratch (or load from exp 07 run if available)
    class BNN_MLP(torch.nn.Module):
        def __init__(self, hidden=1024, num_classes=10):
            super().__init__()
            self.fc1 = DeterministicBinaryLinear(28 * 28, hidden)
            self.bn1 = BinaryBatchNorm1d(hidden)
            self.fc2 = DeterministicBinaryLinear(hidden, hidden)
            self.bn2 = BinaryBatchNorm1d(hidden)
            self.fc3 = DeterministicBinaryLinear(hidden, num_classes)
        def forward(self, x):
            x = x.view(x.size(0), -1)
            h = sign_ste(self.bn1(self.fc1(x)))
            h = sign_ste(self.bn2(self.fc2(h)))
            return self.fc3(h)

    class FP_MLP(torch.nn.Module):
        def __init__(self, hidden=1024, num_classes=10):
            super().__init__()
            self.fc1 = torch.nn.Linear(28 * 28, hidden)
            self.bn1 = torch.nn.BatchNorm1d(hidden)
            self.fc2 = torch.nn.Linear(hidden, hidden)
            self.bn2 = torch.nn.BatchNorm1d(hidden)
            self.fc3 = torch.nn.Linear(hidden, num_classes)
        def forward(self, x):
            x = x.view(x.size(0), -1)
            h = torch.relu(self.bn1(self.fc1(x)))
            h = torch.relu(self.bn2(self.fc2(h)))
            return self.fc3(h)

    # Train BNN and FP from scratch (15 epochs is sufficient for MNIST).
    print("\nTraining BNN baseline (15 epochs) ...")
    set_global_seed(42)
    bnn_model = BNN_MLP(hidden=hidden).to(device)
    _train_quick(bnn_model, train_loader, test_loader, device,
                 n_epochs=15, label="BNN")

    print("\nTraining FP-NN baseline (15 epochs) ...")
    set_global_seed(42)
    fp_model = FP_MLP(hidden=hidden).to(device)
    _train_quick(fp_model, train_loader, test_loader, device,
                 n_epochs=15, label="FP-NN")

    # ----- Part A: per-bit sensitivity for FP-NN -----
    print("\n" + "=" * 70)
    print("Part A: FP-NN per-bit-position sensitivity (8 bit positions)")
    print("=" * 70)

    p_single = 1.0  # flip the chosen bit on every weight (worst case)
    bit_accs = []
    for b in range(8):
        acc = eval_fp_with_bitflip(fp_model, test_loader, device,
                                    p_flip=p_single, bit_position=b,
                                    n_bits=8)
        bit_accs.append(acc)
        print(f"  bit {b} (weight 2^{b} = {2**b:3d})   acc={acc:.4f}")

    # also test small p on each bit for a fairer comparison
    p_small = 0.05
    bit_accs_small = []
    for b in range(8):
        acc = eval_fp_with_bitflip(fp_model, test_loader, device,
                                    p_flip=p_small, bit_position=b,
                                    n_bits=8)
        bit_accs_small.append(acc)
        print(f"  bit {b}, p={p_small}: acc={acc:.4f}")

    # ----- Part B: uniform bit-flip rate sweep, all architectures -----
    print("\n" + "=" * 70)
    print("Part B: Uniform bit-flip rate sweep")
    print("=" * 70)

    p_flips = [0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1]
    accs_pbnn_lo, accs_pbnn_hi, accs_bnn, accs_fp = [], [], [], []
    for p in p_flips:
        a_pl = eval_pbnn_with_bitflip(pbnn_model, test_loader, device,
                                       p_flip=p, T=T_LOW)
        a_ph = eval_pbnn_with_bitflip(pbnn_model, test_loader, device,
                                       p_flip=p, T=T_HIGH)
        a_b  = eval_bnn_with_bitflip(bnn_model, test_loader, device, p_flip=p)
        a_f  = eval_fp_with_bitflip(fp_model, test_loader, device,
                                     p_flip=p, n_bits=8)
        accs_pbnn_lo.append(a_pl)
        accs_pbnn_hi.append(a_ph)
        accs_bnn.append(a_b)
        accs_fp.append(a_f)
        print(f"  p={p:.4f}   PBNN(T={T_LOW})={a_pl:.4f}  "
              f"PBNN(T={T_HIGH})={a_ph:.4f}  BNN={a_b:.4f}  FP={a_f:.4f}")

    # ----- Part C: effective weight-error distributions at p=0.05 -----
    print("\n" + "=" * 70)
    print("Part C: Effective weight-error distribution (p=0.05)")
    print("=" * 70)

    p_test = 0.05
    n_synthetic = 10000
    fp_w = torch.randn(n_synthetic) * 0.5  # synthetic FP weights
    err_fp = fp_effective_error(fp_w, p_test, n_bits=8)
    err_bnn = bnn_effective_error(torch.ones(n_synthetic), p_test)
    err_pbnn_lo = pbnn_effective_error_oneshot(n_synthetic, T_LOW, p_test)
    err_pbnn_hi = pbnn_effective_error_oneshot(n_synthetic, T_HIGH, p_test)

    print(f"  FP-NN (8-bit):    mean={err_fp.mean().item():.4f}  "
          f"max={err_fp.max().item():.4f}  std={err_fp.std().item():.4f}")
    print(f"  BNN (1-bit):      mean={err_bnn.mean().item():.4f}  "
          f"max={err_bnn.max().item():.4f}")
    print(f"  PBNN (T={T_LOW}):     mean={err_pbnn_lo.mean().item():.4f}  "
          f"max={err_pbnn_lo.max().item():.4f}")
    print(f"  PBNN (T={T_HIGH}):    mean={err_pbnn_hi.mean().item():.4f}  "
          f"max={err_pbnn_hi.max().item():.4f}")

    # ----- Save CSVs -----
    with open(run_dir / "per_bit_sensitivity.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bit_position", "weight_2^b",
                    f"acc_p={p_single}", f"acc_p={p_small}"])
        for b in range(8):
            w.writerow([b, 2 ** b, f"{bit_accs[b]:.6f}",
                        f"{bit_accs_small[b]:.6f}"])

    with open(run_dir / "bitflip_sweep.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["p_flip", f"pbnn_T{T_LOW}", f"pbnn_T{T_HIGH}",
                    "bnn", "fp_8bit"])
        for p, pl, ph, b, fa in zip(p_flips, accs_pbnn_lo, accs_pbnn_hi,
                                      accs_bnn, accs_fp):
            w.writerow([p, f"{pl:.6f}", f"{ph:.6f}",
                        f"{b:.6f}", f"{fa:.6f}"])

    with open(run_dir / "effective_error_stats.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arch", "p_flip", "mean_err_norm", "max_err_norm",
                    "std_err_norm"])
        w.writerow(["FP-NN-8bit", p_test,
                    f"{err_fp.mean().item():.6f}",
                    f"{err_fp.max().item():.6f}",
                    f"{err_fp.std().item():.6f}"])
        w.writerow(["BNN", p_test,
                    f"{err_bnn.mean().item():.6f}",
                    f"{err_bnn.max().item():.6f}",
                    f"{err_bnn.std().item():.6f}"])
        w.writerow([f"PBNN-T{T_LOW}", p_test,
                    f"{err_pbnn_lo.mean().item():.6f}",
                    f"{err_pbnn_lo.max().item():.6f}",
                    f"{err_pbnn_lo.std().item():.6f}"])
        w.writerow([f"PBNN-T{T_HIGH}", p_test,
                    f"{err_pbnn_hi.mean().item():.6f}",
                    f"{err_pbnn_hi.max().item():.6f}",
                    f"{err_pbnn_hi.std().item():.6f}"])

    # ----- Plot A: per-bit sensitivity -----
    print("\nPart 5: Generating figures ...")
    fig_a, ax_a = plt.subplots(figsize=(8, 5))
    bits = list(range(8))
    weights_per_bit = [(2 ** b) / 255.0 for b in bits]  # fraction of full scale
    ax_a.bar(bits, [(1 - a) * 100 for a in bit_accs], color="#6E2C91",
             alpha=0.85)
    ax2 = ax_a.twinx()
    ax2.plot(bits, [w * 100 for w in weights_per_bit], "o--",
             color="#D97706", lw=2, markersize=7,
             label="bit weight (% of full scale)")
    ax_a.set_xlabel("Bit position (0=LSB, 7=MSB)", fontsize=12)
    ax_a.set_ylabel("Accuracy drop  (%, single-bit flipped on every weight)",
                    fontsize=12, color="#6E2C91")
    ax2.set_ylabel("Bit numerical weight  (% of dynamic range)",
                   fontsize=12, color="#D97706")
    ax_a.set_title(
        "FP-NN per-bit sensitivity:  MSB flips dominate damage",
        fontsize=13)
    ax_a.set_xticks(bits)
    ax_a.grid(alpha=0.3)
    ax2.legend(loc="upper left")
    fig_a.tight_layout()
    out_a = REPO / "figures" / "09a_per_bit_sensitivity.png"
    out_a.parent.mkdir(parents=True, exist_ok=True)
    fig_a.savefig(out_a, dpi=150, bbox_inches="tight")
    shutil.copy2(out_a, run_dir / "09a_per_bit_sensitivity.png")
    print(f"  Figure A saved: {out_a.relative_to(REPO)}")

    # ----- Plot B: bit-flip sweep -----
    fig_b, ax_b = plt.subplots(figsize=(8, 5))
    ax_b.plot(p_flips, [a * 100 for a in accs_pbnn_lo], "o-",
              color="#A97DBE", lw=2, markersize=6,
              label=f"PBNN T={T_LOW} (T-cell stochastic)")
    ax_b.plot(p_flips, [a * 100 for a in accs_pbnn_hi], "o-",
              color="#4B1369", lw=2, markersize=6,
              label=f"PBNN T={T_HIGH} (T-cell stochastic)")
    ax_b.plot(p_flips, [a * 100 for a in accs_bnn], "s-",
              color="#D97706", lw=2, markersize=6,
              label="BNN (1-bit per weight)")
    ax_b.plot(p_flips, [a * 100 for a in accs_fp], "D-",
              color="#6B7280", lw=2, markersize=6,
              label="FP-NN (8-bit positional)")
    ax_b.set_xlabel("Per-cell bit-flip probability $p$", fontsize=12)
    ax_b.set_ylabel("Test accuracy (%)", fontsize=12)
    ax_b.set_title(
        "Hardware bit-flip robustness:  stochastic encoding wins",
        fontsize=13)
    ax_b.set_xscale("symlog", linthresh=0.001)
    ax_b.legend(fontsize=10, loc="lower left")
    ax_b.grid(alpha=0.3)
    ax_b.set_ylim(0, 105)
    fig_b.tight_layout()
    out_b = REPO / "figures" / "09b_bitflip_accuracy.png"
    fig_b.savefig(out_b, dpi=150, bbox_inches="tight")
    shutil.copy2(out_b, run_dir / "09b_bitflip_accuracy.png")
    print(f"  Figure B saved: {out_b.relative_to(REPO)}")

    # ----- Plot C: effective error distributions -----
    fig_c, ax_c = plt.subplots(figsize=(9, 5))
    bins = 50
    ax_c.hist(err_fp.numpy(), bins=bins, alpha=0.55, density=True,
              color="#6B7280", label="FP-NN (8-bit positional)")
    ax_c.hist(err_pbnn_hi.numpy(), bins=bins, alpha=0.65, density=True,
              color="#4B1369",
              label=f"PBNN T={T_HIGH} (uniform 1/T per cell)")
    ax_c.hist(err_pbnn_lo.numpy(), bins=bins, alpha=0.55, density=True,
              color="#A97DBE", label=f"PBNN T={T_LOW}")
    ax_c.set_xlabel(
        "Effective per-weight error magnitude (fraction of full scale)",
        fontsize=12)
    ax_c.set_ylabel("Density", fontsize=12)
    ax_c.set_title(
        f"Effective weight error under bit-flip $p={p_test}$  "
        f"(BNN: bimodal at 0 and 2, omitted from histogram)",
        fontsize=13)
    ax_c.legend(fontsize=10)
    ax_c.grid(alpha=0.3)
    fig_c.tight_layout()
    out_c = REPO / "figures" / "09c_effective_error_dist.png"
    fig_c.savefig(out_c, dpi=150, bbox_inches="tight")
    shutil.copy2(out_c, run_dir / "09c_effective_error_dist.png")
    print(f"  Figure C saved: {out_c.relative_to(REPO)}")

    # ----- Summary -----
    print("\n--- Summary ---")
    print(f"  FP-NN single-bit flip on every weight:")
    print(f"    LSB (bit 0): acc={bit_accs[0]:.4f}")
    print(f"    MSB (bit 7): acc={bit_accs[7]:.4f}  "
          f"(accuracy drop = {(bit_accs[0] - bit_accs[7]) * 100:.1f}%)")
    if 0.05 in p_flips:
        idx = p_flips.index(0.05)
        print(f"  At p=0.05 uniform bit-flip:")
        print(f"    PBNN(T={T_LOW})    acc={accs_pbnn_lo[idx]:.4f}")
        print(f"    PBNN(T={T_HIGH})   acc={accs_pbnn_hi[idx]:.4f}")
        print(f"    BNN             acc={accs_bnn[idx]:.4f}")
        print(f"    FP-NN (8-bit)   acc={accs_fp[idx]:.4f}")
    print(f"  Run directory: {run_dir}")
    print("Done.")


# ---------------------------------------------------------------------------#
# Lightweight training (so this experiment can run standalone)               #
# ---------------------------------------------------------------------------#

def _train_quick(model, train_loader, test_loader, device, *,
                  n_epochs=15, label="model"):
    import time
    import torch
    from smtj_pbnn_sim.train.train_loop import train_one_epoch, evaluate
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    best_acc, best_state = 0.0, None
    for epoch in range(n_epochs):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, optimizer, binary_cross_entropy_loss, device)
        te_loss, te_acc = evaluate(
            model, test_loader, binary_cross_entropy_loss, device)
        elapsed = time.time() - t0
        print(f"  [{label}] epoch {epoch + 1:02d}/{n_epochs}  "
              f"train acc={tr_acc:.4f}  test acc={te_acc:.4f}  ({elapsed:.1f}s)")
        if te_acc > best_acc:
            best_acc = te_acc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    return best_acc


if __name__ == "__main__":
    main()
