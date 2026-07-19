"""36 -- Paired multi-seed error bars for the headline accuracy gaps.

The chapter's headline accuracy differences (PBNN vs deterministic BNN
0.07 pp, FP32 vs PBNN ~1.5 pp, T=64 vs T=4 0.17 pp) are single-instance
numbers. This experiment retrains all three models with the Experiment-07
recipe under 8 seeds and reports the PAIRED differences (same-seed
subtraction removes the common training variance), which is the
statistically defensible form of each claim.

Per seed: PBNN (hardware-aware training, theta x100 post-scale, BN
calibrated for FULL_STACK), BNN, FP32; evaluated on the full MNIST test
set (PBNN under FULL_STACK T=4 and T=64).

Outputs:
  runs/36_paired_seed_<ts>/paired_bands.csv

Run from the repo root:

    python experiments/36_paired_seed_bands.py
"""

from __future__ import annotations

import csv
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

_spec = importlib.util.spec_from_file_location(
    "exp07", REPO / "experiments" / "07_baseline_comparison.py")
exp07 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exp07)

SEEDS = list(range(8))
N_EPOCHS = 20


def main() -> None:
    import torch
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("36_paired_seed", base=REPO / "runs")
    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=128, num_workers=0)
    BNN_MLP, FP_MLP = exp07._make_models(hidden=1024)

    rows = []
    for seed in SEEDS:
        t0 = time.time()
        set_global_seed(seed)
        pbnn = PBNN_MLP(hidden=1024, device_params=None, variation_cfg=None,
                        T_full_stack=4).to(device)
        pbnn, _ = exp07._train_model(pbnn, train_loader, test_loader, device,
                                     n_epochs=N_EPOCHS, model_name=f"PBNN{seed}")
        with torch.no_grad():
            for m in pbnn.modules():
                if isinstance(m, PBNNLinear):
                    m.theta.mul_(100.0)
        calibrate_bn(pbnn, train_loader, device,
                     mode=ForwardMode.FULL_STACK, T=4)
        acc_t4 = exp07._eval_with_noise(pbnn, test_loader, device, None,
                                        mode=ForwardMode.FULL_STACK, T=4)
        acc_t64 = exp07._eval_with_noise(pbnn, test_loader, device, None,
                                         mode=ForwardMode.FULL_STACK, T=64)

        set_global_seed(seed)
        bnn = BNN_MLP(hidden=1024).to(device)
        bnn, _ = exp07._train_model(bnn, train_loader, test_loader, device,
                                    n_epochs=N_EPOCHS, model_name=f"BNN{seed}")
        acc_bnn = exp07._eval_with_noise(bnn, test_loader, device, None)

        set_global_seed(seed)
        fp = FP_MLP(hidden=1024).to(device)
        fp, _ = exp07._train_model(fp, train_loader, test_loader, device,
                                   n_epochs=N_EPOCHS, model_name=f"FP{seed}")
        acc_fp = exp07._eval_with_noise(fp, test_loader, device, None)

        rows.append({"seed": seed,
                     "pbnn_t4": round(acc_t4 * 100, 2),
                     "pbnn_t64": round(acc_t64 * 100, 2),
                     "bnn": round(acc_bnn * 100, 2),
                     "fp32": round(acc_fp * 100, 2)})
        print(f"seed {seed}: PBNN T4 {acc_t4*100:.2f} T64 {acc_t64*100:.2f} "
              f"BNN {acc_bnn*100:.2f} FP {acc_fp*100:.2f} "
              f"({time.time()-t0:.0f}s)", flush=True)

    a = {k: np.array([r[k] for r in rows]) for k in
         ("pbnn_t4", "pbnn_t64", "bnn", "fp32")}
    pairs = {
        "pbnn_t4_minus_bnn": a["pbnn_t4"] - a["bnn"],
        "fp32_minus_pbnn_t4": a["fp32"] - a["pbnn_t4"],
        "t64_minus_t4": a["pbnn_t64"] - a["pbnn_t4"],
    }
    print("\n--- paired differences (pp, mean +/- std over 8 seeds) ---")
    summary = []
    for k, v in pairs.items():
        print(f"{k:22s}: {v.mean():+.2f} +/- {v.std():.2f}")
        summary.append({"seed": k, "pbnn_t4": round(float(v.mean()), 3),
                        "pbnn_t64": round(float(v.std()), 3),
                        "bnn": "", "fp32": ""})
    with open(run_dir / "paired_bands.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows); w.writerows(summary)
    print(f"CSV written to {run_dir}")


if __name__ == "__main__":
    main()
