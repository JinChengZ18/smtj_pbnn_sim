"""23 -- EOT adaptive-attack audit of the PGD robustness row (Table 4.4).

Audits whether the PBNN PGD advantage reported by Experiment 07 survives
attacks that follow the randomized-defence evaluation protocol (EOT
gradient averaging, Athalye 2018; adaptive-attack checklist, Tramer
2020), and fixes the evaluation-caliber inconsistency of the original
row: the old ``_eval_pgd`` both crafted AND terminally evaluated the
PBNN under HARDWARE_AWARE, while every other row of the comparison is
terminally evaluated under FULL_STACK T=4.

Attack matrix (all at epsilon = 0.1 L_inf on the full MNIST test set):

  * legacy caliber      PGD-10, HARDWARE_AWARE gradient + HW_AWARE eval
  * fixed caliber       PGD-10, HARDWARE_AWARE gradient, FULL_STACK T=4 eval
  * stochastic gradient PGD-10 through FULL_STACK (K=1)
  * EOT-PGD             10/40 steps, K=10/20 gradient draws, 1/3 restarts
  * transfer            PGD-40 crafted on FP-NN / BNN, evaluated on PBNN
  * white-box refs      PGD-10/40 on BNN and FP-NN themselves

The PBNN weights come from the committed ``runs/mnist_pbnn_mlp/best.pt``
checkpoint (same as Experiments 05/07); BNN and FP-NN are retrained with
the Experiment-07 recipe (seed 42, 20 epochs) and their state dicts are
saved into the run directory.

Outputs:
  runs/23_eot_attack_<ts>/attack_matrix.csv
  runs/23_eot_attack_<ts>/{BNN,FP}_state.pt

Run from the repo root:

    python experiments/23_eot_attack_audit.py
"""

from __future__ import annotations

import csv
import importlib.util
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

_spec = importlib.util.spec_from_file_location(
    "exp07", REPO / "experiments" / "07_baseline_comparison.py")
exp07 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exp07)

EPS = 0.1


def main() -> None:
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("23_eot_attack", base=REPO / "runs")
    T = 4

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=256, num_workers=0)

    # ----- PBNN from the committed checkpoint --------------------------------
    ckpt = REPO / "runs" / "mnist_pbnn_mlp" / "best.pt"
    state = torch.load(ckpt, map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    pbnn = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                    device_params=dp, variation_cfg=None,
                    T_full_stack=T).to(device)
    pbnn.load_state_dict(state["model_state"], strict=True)
    calibrate_bn(pbnn, train_loader, device,
                 mode=ForwardMode.FULL_STACK, T=T)

    # ----- BNN / FP-NN retrained with the exp07 recipe -----------------------
    BNN_MLP, FP_MLP = exp07._make_models(hidden=1024)
    set_global_seed(42)
    bnn = BNN_MLP(hidden=1024).to(device)
    bnn, bnn_acc = exp07._train_model(bnn, train_loader, test_loader, device,
                                      n_epochs=20, model_name="BNN")
    set_global_seed(42)
    fp = FP_MLP(hidden=1024).to(device)
    fp, fp_acc = exp07._train_model(fp, train_loader, test_loader, device,
                                    n_epochs=20, model_name="FP")
    torch.save(bnn.state_dict(), run_dir / "BNN_state.pt")
    torch.save(fp.state_dict(), run_dir / "FP_state.pt")

    pbnn_kw = dict(mode=ForwardMode.FULL_STACK, T=T)
    clean = {
        "pbnn": exp07._eval_with_noise(pbnn, test_loader, device, None, **pbnn_kw),
        "bnn": exp07._eval_with_noise(bnn, test_loader, device, None),
        "fp": exp07._eval_with_noise(fp, test_loader, device, None),
    }
    print(f"clean: PBNN(T=4)={clean['pbnn']:.4f}  BNN={clean['bnn']:.4f}  "
          f"FP={clean['fp']:.4f}  (retrained BNN best={bnn_acc:.4f}, "
          f"FP best={fp_acc:.4f})")

    HW, FS = ForwardMode.HARDWARE_AWARE, ForwardMode.FULL_STACK
    MATRIX = [
        # (config label, model, kwargs for _eval_pgd)
        ("pbnn_pgd10_legacy_hw_eval", pbnn,
         dict(mode=HW, eval_mode=HW)),
        ("pbnn_pgd10_fixed_fs_eval", pbnn,
         dict(mode=HW, eval_mode=FS, eval_T=T)),
        ("pbnn_pgd10_fsgrad_K1", pbnn,
         dict(mode=FS, T=T, eval_mode=FS, eval_T=T)),
        ("pbnn_eotpgd10_K10", pbnn,
         dict(mode=FS, T=T, eval_mode=FS, eval_T=T, eot_K=10)),
        ("pbnn_eotpgd40_K10", pbnn,
         dict(mode=FS, T=T, eval_mode=FS, eval_T=T, eot_K=10, n_steps=40)),
        ("pbnn_eotpgd40_K20_r3", pbnn,
         dict(mode=FS, T=T, eval_mode=FS, eval_T=T, eot_K=20, n_steps=40,
              n_restarts=3)),
        ("pbnn_transfer_from_fp_pgd40", pbnn,
         dict(attack_model=fp, mode=None, eval_mode=FS, eval_T=T,
              n_steps=40)),
        ("pbnn_transfer_from_bnn_pgd40", pbnn,
         dict(attack_model=bnn, mode=None, eval_mode=FS, eval_T=T,
              n_steps=40)),
        ("bnn_pgd10", bnn, dict()),
        ("bnn_pgd40_r3", bnn, dict(n_steps=40, n_restarts=3)),
        ("fp_pgd10", fp, dict()),
        ("fp_pgd40_r3", fp, dict(n_steps=40, n_restarts=3)),
    ]

    rows = []
    for label, model, kw in MATRIX:
        t0 = time.time()
        acc = exp07._eval_pgd(model, test_loader, device, EPS, **kw)
        dt = time.time() - t0
        rows.append({
            "config": label, "epsilon": EPS,
            "n_steps": kw.get("n_steps", 10), "eot_K": kw.get("eot_K", 1),
            "n_restarts": kw.get("n_restarts", 1), "accuracy": round(acc, 4),
            "seconds": round(dt, 1),
        })
        print(f"{label:32s} acc={acc:.4f}  ({dt:.0f}s)")

    with open(run_dir / "attack_matrix.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
        w.writerow({"config": "clean_pbnn", "epsilon": 0, "n_steps": 0,
                    "eot_K": 0, "n_restarts": 0,
                    "accuracy": round(clean["pbnn"], 4), "seconds": 0})
        w.writerow({"config": "clean_bnn", "epsilon": 0, "n_steps": 0,
                    "eot_K": 0, "n_restarts": 0,
                    "accuracy": round(clean["bnn"], 4), "seconds": 0})
        w.writerow({"config": "clean_fp", "epsilon": 0, "n_steps": 0,
                    "eot_K": 0, "n_restarts": 0,
                    "accuracy": round(clean["fp"], 4), "seconds": 0})
    print(f"matrix saved: {run_dir / 'attack_matrix.csv'}")

    get = {r["config"]: r["accuracy"] for r in rows}
    print("\n--- Audit summary ---")
    print(f"legacy caliber (HW eval)     : {get['pbnn_pgd10_legacy_hw_eval']:.4f}")
    print(f"fixed caliber  (FS T=4 eval) : {get['pbnn_pgd10_fixed_fs_eval']:.4f}")
    print(f"strongest EOT  (40/K20/r3)   : {get['pbnn_eotpgd40_K20_r3']:.4f}")
    print(f"BNN  PGD-40/r3               : {get['bnn_pgd40_r3']:.4f}")
    print(f"FP   PGD-40/r3               : {get['fp_pgd40_r3']:.4f}")


if __name__ == "__main__":
    main()
