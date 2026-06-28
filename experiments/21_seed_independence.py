"""21 -- Seed-independence of the headline results (reviewer robustness check).

A reviewer asked whether the headline numbers were cherry-picked by a lucky RNG
seed. This script re-runs the four flagship conclusions across many independent
seeds and reports each as mean +/- std, demonstrating the conclusions are a
property of the method, not of one seed:

  1. PBNN-MLP MNIST test accuracy            (experiments/05 core: train per seed)
  2. Time-domain unfolding accuracy vs T      (experiments/06 core: T-sweep per seed)
  3. sMTJ-RC memory capacity + energy gain    (experiments/16 core: stochastic MC)
  4. Device sigmoid slope beta_s at CV=7.7%   (experiments/02 core: wafer-average MC)

Everything reuses the same library functions the headline experiments use; only
the seed is swept. Results are written incrementally to
``runs/21_seed_independence/seed_independence.json`` (so a long run can be
inspected mid-flight) and summarised in ``figures/21_seed_independence.png``.

Run from the repo root (optionally pass the number of seeds, default 8):

    python experiments/21_seed_independence.py [n_seeds]
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import time

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

PURPLE, RED, DEEP, GREEN, GOLD = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#D4A017"
N_SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 8
SEEDS = list(range(N_SEEDS))
RUN = REPO / "runs" / "21_seed_independence"
RUN.mkdir(parents=True, exist_ok=True)
JSON_OUT = RUN / "seed_independence.json"
T_LIST = [1, 4, 16, 64]


# --------------------------------------------------------------------------- #
# 1 + 2: PBNN MNIST accuracy and the T-sweep, trained fresh per seed.
# --------------------------------------------------------------------------- #
def pbnn_and_tsweep(seed: int) -> dict:
    import csv
    import torch
    from smtj_pbnn_sim.utils.io import load_yaml, make_run_dir
    from smtj_pbnn_sim.scripts._mnist_train import run, PBNN_MLP
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.nn.losses import binary_cross_entropy_loss
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import evaluate, calibrate_bn
    from smtj_pbnn_sim.ppa import default_28nm, layer_inference_energy

    cfg = load_yaml(REPO / "configs" / "experiment" / "mnist_lenet.yaml")
    cfg["seed"] = seed                      # the only thing we vary
    out = make_run_dir(f"21_pbnn_seed{seed}", base=RUN)
    if run(cfg, out) != 0:
        raise RuntimeError(f"PBNN training failed at seed {seed}")

    best_acc = max(float(r["test_acc"]) for r in csv.DictReader(open(out / "metrics.csv", encoding="utf-8")))

    # T-sweep on the freshly trained checkpoint (FULL_STACK, BN recalibrated per T)
    state = torch.load(out / "best.pt", map_location="cpu")
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dp = _device_params_from_cfg(state["config"].get("device", {}))
    mcfg = state["config"].get("model", {})
    tr, te = get_mnist_loaders(root=cfg["data"]["root"],
                               batch_size=int(cfg["data"]["batch_size"]), num_workers=0)
    tech = default_28nm()
    acc_T, e_T = {}, {}
    for T in T_LIST:
        m = PBNN_MLP(hidden=int(mcfg.get("hidden", 1024)), device_params=dp,
                     variation_cfg=None, T_full_stack=T).to(dev)
        m.load_state_dict(state["model_state"], strict=True)
        calibrate_bn(m, tr, dev, mode=ForwardMode.FULL_STACK, T=T, num_batches=50)
        _, acc = evaluate(m, te, binary_cross_entropy_loss, dev, mode=ForwardMode.FULL_STACK, T=T)
        acc_T[T] = float(acc)
        e_T[T] = float(3 * layer_inference_energy(256, 256, T, tech))
    return {"best_acc": best_acc, "acc_T": acc_T, "energy_T_uJ": {T: e_T[T] * 1e6 for T in T_LIST}}


# --------------------------------------------------------------------------- #
# 3: sMTJ-RC memory capacity + energy advantage, stochastic reservoir per seed.
# --------------------------------------------------------------------------- #
def rc_metrics(seed: int) -> dict:
    from smtj_pbnn_sim.reservoir import ReservoirConfig, SMTJReservoir, memory_capacity, tasks
    from smtj_pbnn_sim.ppa import (default_28nm, ReservoirHW,
                                   smtj_rc_inference_energy, digital_esn_inference_energy)
    N, L, DT, ENS = 100, 1000, 25e-9, 96
    tech = default_28nm()
    u = tasks.memory_capacity_inputs(1100, seed=seed)
    cfg = ReservoirConfig(n_nodes=N, mode="stochastic", effective_spectral_radius=0.5,
                          effective_input_scale=2.0, dt=DT, substeps=25, ensemble=ENS, seed=seed)
    mc = memory_capacity(SMTJReservoir(cfg, 1).run(u, washout=100), u[100:], max_delay=25)[0]
    cfg_mf = ReservoirConfig(n_nodes=N, mode="meanfield", effective_spectral_radius=0.5,
                             effective_input_scale=2.0, dt=DT, seed=seed)
    mc_dig = memory_capacity(SMTJReservoir(cfg_mf, 1).run(u, washout=100), u[100:], max_delay=25)[0]
    e_rc = smtj_rc_inference_energy(ReservoirHW(n_nodes=N, ensemble=ENS, dt=DT), tech, L)
    e_dig = digital_esn_inference_energy(N, tech, L, memory="sram_cim", digital_mac=True)
    # Headline energy advantage = structural inference-energy ratio (deterministic,
    # seed-independent by construction); memory capacity is the seed-sensitive accuracy.
    return {"mc": float(mc), "mc_digital": float(mc_dig), "energy_adv": float(e_dig / e_rc)}


# --------------------------------------------------------------------------- #
# 4: device sigmoid slope beta_s at the PDK baseline CV(Delta)=7.7%, per seed.
# --------------------------------------------------------------------------- #
def device_beta_s(seed: int) -> dict:
    import math
    import pandas as pd
    from smtj_pbnn_sim.device.arrhenius import psw_neel_brown
    from smtj_pbnn_sim.device.calibration import fit_sigmoid_params
    DELTA, VC0, TAU0, TP, N_DEV, CV = 4.91, 0.857, 1.0e-9, 0.75e-9, 20_000, 0.077
    rng = np.random.default_rng(seed)
    Di = np.maximum(DELTA * (1.0 + CV * rng.standard_normal(N_DEV)), 0.5)
    V = np.linspace(0.78, 1.10, 81)
    P = np.zeros_like(V)
    for D in Di:
        P += psw_neel_brown(V, t_p=TP, tau_0=TAU0, Delta=D, V_c0=VC0)
    P /= N_DEV
    sp = fit_sigmoid_params(pd.DataFrame({"V": V, "P_sw": P, "t_p": TP}))
    return {"beta_s": float(sp.beta_s), "V_th_mV": float(sp.V_th * 1e3), "r2": float(sp.r2)}


def _stats(xs):
    a = np.asarray(xs, float)
    return {"mean": float(a.mean()), "std": float(a.std(ddof=1) if len(a) > 1 else 0.0),
            "min": float(a.min()), "max": float(a.max()), "n": len(a)}


def main() -> None:
    t0 = time.time()
    results = {"seeds": SEEDS, "T_list": T_LIST, "per_seed": {}}
    for s in SEEDS:
        print(f"\n=== seed {s} ({SEEDS.index(s) + 1}/{len(SEEDS)}) ===")
        rec = {}
        rec["device"] = device_beta_s(s); print(f"  device beta_s = {rec['device']['beta_s']:.2f}")
        rec["rc"] = rc_metrics(s); print(f"  RC MC = {rec['rc']['mc']:.2f}, adv = {rec['rc']['energy_adv']:.0f}x")
        rec["pbnn"] = pbnn_and_tsweep(s)
        print(f"  PBNN best acc = {rec['pbnn']['best_acc'] * 100:.2f}%, "
              f"acc(T=4)={rec['pbnn']['acc_T'][4] * 100:.2f}%, acc(T=64)={rec['pbnn']['acc_T'][64] * 100:.2f}%")
        results["per_seed"][s] = rec
        JSON_OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")   # incremental

    # ---- aggregate ----
    acc = [results["per_seed"][s]["pbnn"]["best_acc"] * 100 for s in SEEDS]
    gap = [(results["per_seed"][s]["pbnn"]["acc_T"][64] - results["per_seed"][s]["pbnn"]["acc_T"][4]) * 100 for s in SEEDS]
    mc = [results["per_seed"][s]["rc"]["mc"] for s in SEEDS]
    adv = [results["per_seed"][s]["rc"]["energy_adv"] for s in SEEDS]
    beta = [results["per_seed"][s]["device"]["beta_s"] for s in SEEDS]
    results["summary"] = {"pbnn_best_acc_pct": _stats(acc), "tsweep_gap_T64_minus_T4_pp": _stats(gap),
                          "rc_memory_capacity": _stats(mc), "rc_energy_adv_x": _stats(adv),
                          "device_beta_s": _stats(beta)}
    JSON_OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\n--- summary (mean +/- std over %d seeds) ---" % len(SEEDS))
    for k, v in results["summary"].items():
        print(f"  {k:34s} = {v['mean']:.3f} +/- {v['std']:.3f}  [{v['min']:.3f}, {v['max']:.3f}]")

    # ---- figure ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3})
    fig, ax = plt.subplots(2, 2, figsize=(13, 9))

    def strip(a, vals, color, ylabel, title, pct=False):
        m, sd = np.mean(vals), np.std(vals, ddof=1) if len(vals) > 1 else 0.0
        a.axhspan(m - sd, m + sd, color=color, alpha=0.15)
        a.axhline(m, color=color, lw=1.6, ls="--")
        a.scatter(SEEDS, vals, s=55, color=color, edgecolor="black", zorder=3)
        a.set_xlabel("random seed"); a.set_ylabel(ylabel); a.set_title(title)
        a.annotate(f"{m:.2f} $\\pm$ {sd:.2f}" + (" pp" if pct else ""), xy=(0.5, 0.92),
                   xycoords="axes fraction", ha="center", fontsize=10, color=color, fontweight="bold")

    strip(ax[0, 0], acc, PURPLE, "test accuracy (%)", "PBNN MNIST accuracy")
    for s in SEEDS:
        at = results["per_seed"][s]["pbnn"]["acc_T"]
        ax[0, 1].plot(T_LIST, [at[T] * 100 for T in T_LIST], "o-", color=DEEP, alpha=0.55, lw=1.2)
    ax[0, 1].set_xscale("log", base=2); ax[0, 1].set_xlabel("samples per inference T")
    ax[0, 1].set_ylabel("test accuracy (%)"); ax[0, 1].set_title("Accuracy vs T (one line per seed)")
    strip(ax[1, 0], mc, RED, "memory capacity", "Reservoir memory capacity")
    strip(ax[1, 1], beta, GREEN, r"$\beta_s$ (V$^{-1}$)", "Device sigmoid slope at CV=7.7%")
    fig.tight_layout()
    out = REPO / "figures" / "21_seed_independence.png"
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure: {out.relative_to(REPO)}\nJSON: {JSON_OUT.relative_to(REPO)}\nRuntime: {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
