"""05 -- MNIST PBNN-MLP training (requires PyTorch).

Trains the 3-layer PBNN-MLP defined in
``smtj_pbnn_sim.scripts._mnist_train`` using the Chapter-2.3 primary
reference device parameters and PDK-baseline variation.

Run from the repo root:

    python experiments/05_mnist_pbnn.py

This script is a thin wrapper around the CLI's training entry; for full
control use ``smtj-train --config configs/experiment/mnist_lenet.yaml``.
"""

from __future__ import annotations

from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def main() -> None:
    try:
        import torch  # noqa: F401
    except ImportError:
        print("PyTorch is required for this experiment.")
        print("Install with: pip install torch torchvision")
        sys.exit(1)

    from smtj_pbnn_sim.utils.io import load_yaml
    from smtj_pbnn_sim.scripts._mnist_train import run

    cfg_path = REPO / "configs" / "experiment" / "mnist_lenet.yaml"
    cfg = load_yaml(cfg_path)
    out_dir = REPO / "runs" / cfg.get("name", "mnist_pbnn_mlp")
    sys.exit(run(cfg, out_dir))


if __name__ == "__main__":
    main()
