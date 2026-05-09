"""07 -- Variation sweep: test accuracy vs. CV(Delta) (requires PyTorch).

Reloads a trained model and re-evaluates with progressively larger
device-to-device variation, holding the trained theta fixed. This is the
"cold-start" robustness curve: how does inference quality degrade if the
deployed wafer is more variable than the calibration wafer?

Run from the repo root:

    python experiments/07_variation_sweep.py
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

    from smtj_pbnn_sim.device.variation import VariationConfig
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import evaluate
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP

    ckpt_path = REPO / "runs" / "mnist_pbnn_mlp" / "best.pt"
    if not ckpt_path.exists():
        print(f"Checkpoint not found at {ckpt_path}; run 05 first.")
        sys.exit(1)

    state = torch.load(ckpt_path, map_location="cpu")
    cfg = state["config"]
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dp = _device_params_from_cfg(cfg.get("device", {}))
    model_cfg = cfg.get("model", {})

    _, test_loader = get_mnist_loaders(
        root=cfg.get("data", {}).get("root", "./data/mnist"),
        batch_size=int(cfg.get("data", {}).get("batch_size", 128)),
        num_workers=2,
    )

    cvs = [0.0, 0.05, 0.077, 0.10, 0.15, 0.20, 0.30, 0.50]
    accs = []
    for cv in cvs:
        vc = VariationConfig(mode="delta", cv_delta=cv, seed=42)
        model = PBNN_MLP(hidden=int(model_cfg.get("hidden", 1024)),
                          device_params=dp, variation_cfg=vc,
                          T_full_stack=16).to(dev)
        model.load_state_dict(state["model_state"], strict=True)
        _, acc = evaluate(model, test_loader, binary_cross_entropy_loss, dev,
                          mode=ForwardMode.HARDWARE_AWARE)
        accs.append(acc)
        print(f"  CV(Delta) = {cv*100:5.1f} %   acc = {acc:.4f}")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot([cv * 100 for cv in cvs], accs, "o-", color="#5E3F8C", lw=2)
    ax.axvline(7.7, color="#C47A00", ls="--",
               label="PDK baseline 7.7%")
    ax.set_xlabel("CV($\\Delta$) (%)")
    ax.set_ylabel("Test accuracy")
    ax.set_title("MNIST PBNN-MLP accuracy vs. wafer variation")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    out = REPO / "figures" / "07_variation_sweep.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"Figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
