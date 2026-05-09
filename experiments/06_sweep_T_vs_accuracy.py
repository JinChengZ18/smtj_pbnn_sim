"""06 -- Sweep T_full_stack vs. test accuracy (requires PyTorch).

After training a model with ``05_mnist_pbnn.py``, this script reloads the
checkpoint and evaluates the network at T = 1, 2, 4, ..., 64 in
FULL_STACK mode. It plots accuracy vs T and accuracy vs total inference
energy (per the PPA tech params), demonstrating the time-domain unfolding
trade-off.

Run from the repo root:

    python experiments/06_sweep_T_vs_accuracy.py
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def main() -> None:
    try:
        import torch
        import matplotlib.pyplot as plt
    except ImportError:
        print("PyTorch and matplotlib are required for this experiment.")
        sys.exit(1)

    import csv
    import shutil
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import evaluate, calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.ppa import default_28nm, layer_inference_energy

    ckpt_path = REPO / "runs" / "mnist_pbnn_mlp" / "best.pt"
    if not ckpt_path.exists():
        print(f"Checkpoint not found at {ckpt_path}.")
        print("Run experiments/05_mnist_pbnn.py first.")
        sys.exit(1)

    run_dir = make_run_dir("06_sweep_T", base=REPO / "runs")

    state = torch.load(ckpt_path, map_location="cpu")
    cfg = state["config"]
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dp = _device_params_from_cfg(cfg.get("device", {}))
    # Use variation_cfg=None for FULL_STACK evaluation: training used
    # HARDWARE_AWARE mode where hard binary weights sign(theta) are
    # insensitive to variation in the forward pass. The delta-mode NB
    # bridge centers V_th at ~0.843V vs V_th_nom=0.894V, creating a
    # systematic 50mV offset that corrupts FULL_STACK probabilities.
    vc = None
    model_cfg = cfg.get("model", {})

    train_loader, test_loader = get_mnist_loaders(
        root=cfg.get("data", {}).get("root", "./data/mnist"),
        batch_size=int(cfg.get("data", {}).get("batch_size", 128)),
        num_workers=0,
    )

    Ts = [1, 2, 4, 8, 16, 32, 64]
    accs, energies = [], []
    tech = default_28nm()

    for T in Ts:
        model = PBNN_MLP(hidden=int(model_cfg.get("hidden", 1024)),
                          device_params=dp, variation_cfg=vc,
                          T_full_stack=T).to(dev)
        model.load_state_dict(state["model_state"], strict=True)
        calibrate_bn(model, train_loader, dev,
                     mode=ForwardMode.FULL_STACK, T=T, num_batches=50)
        _, acc = evaluate(model, test_loader, binary_cross_entropy_loss, dev,
                          mode=ForwardMode.FULL_STACK, T=T)
        e = 3 * layer_inference_energy(256, 256, T, tech)
        accs.append(acc)
        energies.append(e)
        print(f"  T = {T:3d}   acc = {acc:.4f}   E ~= {e*1e6:.3f} uJ")

    # Save results CSV
    csv_path = run_dir / "results.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["T", "accuracy", "energy_uJ"])
        for t, a, e in zip(Ts, accs, energies):
            w.writerow([t, f"{a:.6f}", f"{e*1e6:.6f}"])
    print(f"Results saved: {csv_path}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].plot(Ts, accs, "o-", color="#5E3F8C", lw=2)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("Number of stochastic samples per inference, T")
    axes[0].set_ylabel("Test accuracy")
    axes[0].set_title("Accuracy vs. sampling count T")
    axes[0].grid(alpha=0.3, which="both")

    axes[1].plot([e * 1e6 for e in energies], accs, "s-",
                 color="#A82038", lw=2)
    axes[1].set_xscale("log")
    axes[1].set_xlabel("Per-inference energy (uJ)")
    axes[1].set_ylabel("Test accuracy")
    axes[1].set_title("Accuracy vs. inference energy")
    axes[1].grid(alpha=0.3, which="both")

    fig.tight_layout()
    out = REPO / "figures" / "06_sweep_T.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    shutil.copy2(out, run_dir / "06_sweep_T.png")
    print(f"Figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
