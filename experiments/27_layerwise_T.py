"""27 -- Layer-wise sampling-budget allocation at iso energy.

T is the PBNN's central resource, but the pipeline so far spends it
uniformly (the same T at every layer). Because the per-sample cost of a
layer scales with its MAC count, the three MLP layers price their samples
very differently -- L1 (784x1024) and L2 (1024x1024) carry ~99.4% of the
energy while the classifier layer L3 (1024x10) is nearly free. This
experiment measures (a) the per-layer accuracy sensitivity to T and
(b) whether re-allocating a fixed energy budget across layers (water-
filling the cheap classifier layer with samples shaved off the expensive
layers) buys accuracy at iso energy.

Per-layer T uses the library's ``sampling.schedules`` helpers and the
``T_full_stack`` per-layer attribute (forward with T=None applies each
layer's own value); BatchNorm running stats are recalibrated for every
schedule so the comparison is fair.

Outputs:
  runs/27_layerwise_T_<ts>/{sensitivity.csv, schedules.csv}
  figures/27_layerwise_T.png

Run from the repo root:

    python experiments/27_layerwise_T.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

T_BASE = 4
SENS_GRID = [1, 2, 4, 8, 16]
N_REPS = 3


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.sampling.schedules import constant_T, layer_depth_T
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.ppa.tech_params import default_28nm
    from smtj_pbnn_sim.ppa.energy import per_mac_energy

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("27_layerwise_T", base=REPO / "runs")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=500, num_workers=0)
    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                     device_params=dp, variation_cfg=None,
                     T_full_stack=T_BASE).to(device)
    model.load_state_dict(state["model_state"], strict=True)
    layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]
    macs = [m.in_features * m.out_features for m in layers]
    tech = default_28nm()
    e_mac = per_mac_energy(tech)
    budget0 = T_BASE * sum(macs)
    print(f"layer MACs: {macs} (shares "
          f"{[round(m/sum(macs)*100, 1) for m in macs]} %); "
          f"iso budget = {budget0/1e6:.3f} M sample-MACs "
          f"= {budget0*e_mac*1e6:.2f} uJ/decision")

    def set_schedule(Ts):
        for m, t in zip(layers, Ts):
            m.T_full_stack = int(t)
        calibrate_bn(model, train_loader, device,
                     mode=ForwardMode.FULL_STACK, T=None)

    def evaluate(rep_seed: int) -> float:
        torch.manual_seed(rep_seed)
        n_ok = n = 0
        with torch.no_grad():
            for x, y in test_loader:
                x, y = x.to(device), y.to(device)
                logits = model.forward_with_mode(
                    x, mode=ForwardMode.FULL_STACK, T=None)
                n_ok += int((logits.argmax(1) == y).sum())
                n += int(y.numel())
        return n_ok / n

    # ----- (a) one-layer-at-a-time sensitivity ----------------------------
    sens_rows = []
    for li in range(len(layers)):
        for t in SENS_GRID:
            Ts = constant_T(len(layers), T_BASE)
            Ts[li] = t
            set_schedule(Ts)
            accs = [evaluate(100 + r) for r in range(2)]
            sens_rows.append({"layer": li + 1, "T": t,
                              "acc_mean": round(float(np.mean(accs)), 4),
                              "acc_std": round(float(np.std(accs)), 4)})
            print(f"  sens L{li+1} T={t:2d}: {np.mean(accs):.4f} "
                  f"+/- {np.std(accs):.4f}")

    # ----- (b) iso-energy schedules ----------------------------------------
    def fill_T3(t1, t2):
        rem = budget0 - t1 * macs[0] - t2 * macs[1]
        return max(1, int(rem // macs[2]))

    schedules = {
        "uniform (4,4,4)": constant_T(3, T_BASE),
        "shave L1 (3,4,fill)": [3, 4, fill_T3(3, 4)],
        "shave L2 (4,3,fill)": [4, 3, fill_T3(4, 3)],
        "shave both (3,3,fill)": [3, 3, fill_T3(3, 3)],
        "L2-heavy (2,5,fill)": [2, 5, fill_T3(2, 5)],
        "L1-heavy (5,3,fill)": [5, 3, fill_T3(5, 3)],
        "depth ramp (2,4,fill)": [layer_depth_T(3, 2, 6)[0],
                                  layer_depth_T(3, 2, 6)[1], fill_T3(2, 4)],
        "free L3 boost (4,4,64)": [4, 4, 64],   # +0.8% energy, NOT iso
    }
    sched_rows = []
    for name, Ts in schedules.items():
        cost = sum(t * m for t, m in zip(Ts, macs))
        set_schedule(Ts)
        accs = [evaluate(200 + r) for r in range(N_REPS)]
        sched_rows.append({
            "schedule": name, "T1": Ts[0], "T2": Ts[1], "T3": Ts[2],
            "energy_rel": round(cost / budget0, 4),
            "acc_mean": round(float(np.mean(accs)), 4),
            "acc_std": round(float(np.std(accs)), 4)})
        print(f"  sched {name:24s} T={Ts} E/E0={cost/budget0:.3f} "
              f"acc={np.mean(accs):.4f} +/- {np.std(accs):.4f}")

    with open(run_dir / "sensitivity.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sens_rows[0]))
        w.writeheader(); w.writerows(sens_rows)
    with open(run_dir / "schedules.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sched_rows[0]))
        w.writeheader(); w.writerows(sched_rows)
    print(f"CSVs written to {run_dir}")

    # ----- figure -----------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.0))
    colors = {1: "#5E3F8C", 2: "#A82038", 3: "#1A6B5A"}
    for li in (1, 2, 3):
        pts = [r for r in sens_rows if r["layer"] == li]
        ax[0].errorbar([r["T"] for r in pts],
                       [r["acc_mean"] * 100 for r in pts],
                       yerr=[r["acc_std"] * 100 for r in pts],
                       fmt="o-", lw=2, capsize=3, color=colors[li],
                       label=f"layer {li} (others at T={T_BASE})")
    ax[0].set_xscale("log", base=2)
    ax[0].set_xlabel("layer sample count T")
    ax[0].set_ylabel("MNIST test accuracy (%)")
    ax[0].set_title("Per-layer sensitivity to T")
    ax[0].legend(fontsize=9); ax[0].grid(alpha=0.3)

    names = [r["schedule"] for r in sched_rows]
    y = np.arange(len(names))
    accs = [r["acc_mean"] * 100 for r in sched_rows]
    errs = [r["acc_std"] * 100 for r in sched_rows]
    base_acc = accs[0]
    bars = ax[1].barh(y, accs, xerr=errs, height=0.62, capsize=3,
                      color=["#5E3F8C"] + ["#9580BD"] * (len(names) - 2)
                      + ["#C99FD4"])
    ax[1].axvline(base_acc, color="k", ls="--", lw=1.2)
    ax[1].set_yticks(y)
    ax[1].set_yticklabels([f"{n}\nE/E0={r['energy_rel']:.2f}"
                           for n, r in zip(names, sched_rows)], fontsize=9)
    ax[1].invert_yaxis()
    lo = min(a - e for a, e in zip(accs, errs)) - 0.1
    hi = max(a + e for a, e in zip(accs, errs)) + 0.1
    ax[1].set_xlim(lo, hi)
    ax[1].set_xlabel("MNIST test accuracy (%)")
    ax[1].set_title("Iso-energy schedules (last bar: +0.8% energy)")
    ax[1].grid(alpha=0.3, axis="x")
    fig.tight_layout()
    out = REPO / "figures" / "27_layerwise_T.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
