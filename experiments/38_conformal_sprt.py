"""38 -- Input-adaptive sampling: sequential stopping with conformal coverage.

Experiments 06 and 27 fix the sampling depth T for the whole test set,
which pays the worst-case sample count on every input. The Bernoulli
samples arrive one at a time, so the natural alternative is to stop as
soon as the running class posterior is decisive -- a Wald-style
sequential test on the same samples the inference would draw anyway,
with no extra circuitry.

Sequential stopping breaks the exchangeability that split conformal
prediction relies on, so the procedure is fixed BEFORE calibration: the
stopping rule runs on the calibration split as well, and the conformal
quantile is taken over the scores AT THE STOPPING TIME. The resulting
prediction sets keep the marginal coverage guarantee of split conformal
for the adaptive predictor as a whole.

Protocol (MNIST PBNN-MLP checkpoint, FULL_STACK single-sample members):
  * draw M_max single-sample probability vectors per test image once,
    then evaluate every stopping rule offline on the same draws;
  * stopping rule: stop at the first m where the running vote margin
    between the leading and the runner-up class reaches b;
  * split: first half calibration, second half evaluation;
  * report mean sample count, top-1 accuracy, conformal coverage and
    average set size at alpha = 0.05 and 0.10, against the fixed-T
    procedure calibrated identically.

Outputs:
  runs/38_conformal_sprt_<ts>/adaptive.csv
  runs/38_conformal_sprt_<ts>/fixed_T.csv
  figures/38_conformal_sprt.png

Run from the repo root:

    python experiments/38_conformal_sprt.py
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

M_MAX = 64
B_GRID = [1, 2, 3, 4, 6, 8, 12, 16]      # required vote margin
T_GRID = [1, 2, 4, 8, 16, 32, 64]
ALPHAS = [0.05, 0.10]


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn, _forward_with_mode
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.ppa.tech_params import default_28nm
    from smtj_pbnn_sim.ppa.energy import per_mac_energy

    t0 = time.time()
    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("38_conformal_sprt", base=REPO / "runs")
    print(f"device: {device}")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=500, num_workers=0)
    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                     device_params=_device_params_from_cfg(cfg.get("device", {})),
                     variation_cfg=None, T_full_stack=1).to(device)
    model.load_state_dict(state["model_state"], strict=True)
    calibrate_bn(model, train_loader, device, mode=ForwardMode.FULL_STACK, T=1)
    model.eval()

    # ---- draw M_MAX single-sample posteriors per image, once ---------------
    probs, ys = [], []
    with torch.no_grad():
        for x, y in test_loader:
            x = x.to(device)
            p = torch.stack([
                torch.softmax(_forward_with_mode(model, x,
                                                 ForwardMode.FULL_STACK), -1)
                for _ in range(M_MAX)], 0)             # (M, B, C)
            probs.append(p.cpu())
            ys.append(y)
    P = torch.cat(probs, 1).numpy()                    # (M_MAX, N, C)
    Y = torch.cat(ys).numpy()
    N = len(Y)
    print(f"drew {M_MAX} single-sample posteriors for {N} images "
          f"({time.time()-t0:.0f}s)")

    run_mean = np.cumsum(P, axis=0) / np.arange(1, M_MAX + 1)[:, None, None]
    # Sequential statistic: the running VOTE margin between the leading and
    # the runner-up class. The theta x100 post-scaling makes each single
    # sample almost one-hot, so the within-sample softmax gap carries no
    # information; what accumulates across samples is the vote count, which
    # is also what a popcount read-out physically produces.
    votes = np.cumsum(np.eye(P.shape[2])[P.argmax(2)], axis=0)   # (M, N, C)
    vs = np.sort(votes, axis=2)
    gap = vs[:, :, -1] - vs[:, :, -2]                   # (M, N) vote margin

    cal = np.arange(N) < N // 2
    ev = ~cal
    tech = default_28nm()
    macs = 784 * 1024 + 1024 * 1024 + 1024 * 10
    e_mac = per_mac_energy(tech)

    def conformal(scores_cal, scores_ev_all, alpha):
        """Split-conformal quantile from calibration scores; returns the
        threshold and the evaluation-set coverage/set size."""
        n = len(scores_cal)
        k = int(np.ceil((n + 1) * (1 - alpha)))
        q = np.sort(scores_cal)[min(k, n) - 1]
        inset = scores_ev_all <= q                      # (N_ev, C)
        return float(q), inset

    def summarise(mean_probs, stop_m, tag, extra):
        """Accuracy + conformal coverage/set size for one stopped predictor."""
        pred = mean_probs.argmax(1)
        acc_ev = float((pred[ev] == Y[ev]).mean())
        s_all = 1.0 - mean_probs                        # non-conformity score
        s_true_cal = s_all[cal, Y[cal]]
        acc_all = float((pred == Y).mean())
        row = {"rule": tag, **extra,
               "mean_samples": round(float(stop_m.mean()), 3),
               "accuracy_all": round(acc_all, 4),
               "p95_samples": int(np.percentile(stop_m, 95)),
               "accuracy": round(acc_ev, 4),
               "energy_uJ": round(float(stop_m.mean()) * macs * e_mac * 1e6, 3)}
        for a in ALPHAS:
            q, inset = conformal(s_true_cal, s_all[ev], a)
            empty = float((~inset.any(1)).mean())
            # the top-1 class is always kept, so no input is returned an empty
            # set; adding elements can only raise coverage above the guarantee
            inset[np.arange(inset.shape[0]), pred[ev]] = True
            cov = float(inset[np.arange(inset.shape[0]), Y[ev]].mean())
            row[f"coverage_a{int(a*100)}"] = round(cov, 4)
            row[f"setsize_a{int(a*100)}"] = round(float(inset.sum(1).mean()), 3)
            row[f"empty_raw_a{int(a*100)}"] = round(empty, 4)
        return row

    # ---- fixed-T reference -------------------------------------------------
    fixed = []
    for T in T_GRID:
        mp = run_mean[T - 1]
        fixed.append(summarise(mp, np.full(N, T, dtype=float),
                               "fixed", {"param": T}))
        r = fixed[-1]
        print(f"fixed  T={T:2d}: acc={r['accuracy']:.4f} "
              f"cov(5%)={r['coverage_a5']:.4f} set={r['setsize_a5']:.3f} "
              f"E={r['energy_uJ']:.2f} uJ")

    # ---- adaptive sequential stopping --------------------------------------
    adaptive = []
    for h in B_GRID:
        hit = gap >= h                                  # (M, N)
        first = np.where(hit.any(0), hit.argmax(0), M_MAX - 1)
        mp = run_mean[first, np.arange(N)]
        adaptive.append(summarise(mp, first + 1.0, "adaptive", {"param": h}))
        r = adaptive[-1]
        print(f"adapt b={h:2d}: mean M={r['mean_samples']:5.2f} "
              f"p95={r['p95_samples']:2d} acc={r['accuracy']:.4f} "
              f"cov(5%)={r['coverage_a5']:.4f} set={r['setsize_a5']:.3f} "
              f"E={r['energy_uJ']:.2f} uJ")

    for name, rows in (("fixed_T.csv", fixed), ("adaptive.csv", adaptive)):
        with open(run_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    print(f"CSV written to {run_dir}")

    # iso-accuracy comparison: cheapest adaptive rule matching fixed T=4
    ref = next(r for r in fixed if r["param"] == 4)
    ok = [r for r in adaptive if r["accuracy"] >= ref["accuracy"] - 0.0005]
    if ok:
        best = min(ok, key=lambda r: r["mean_samples"])
        print(f"iso-accuracy vs fixed T=4 ({ref['accuracy']:.4f}): "
              f"b={best['param']} needs mean M={best['mean_samples']:.2f} "
              f"({100*(1-best['mean_samples']/4):.1f}% fewer samples), "
              f"coverage {best['coverage_a5']:.4f} vs {ref['coverage_a5']:.4f}")

    # ---- figure ------------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 2, figsize=(11.0, 4.8))

    ax[0].plot([r["mean_samples"] for r in fixed],
               [r["accuracy_all"] * 100 for r in fixed], "o-",
               color="#A82038", lw=2)
    ax[0].plot([r["mean_samples"] for r in adaptive],
               [r["accuracy_all"] * 100 for r in adaptive], "s-",
               color="#5E3F8C", lw=2)
    ax[0].set_xscale("log", base=2)
    ax[0].text(fixed[-1]["mean_samples"], fixed[-1]["accuracy_all"] * 100,
               "fixed depth ", fontsize=11, color="#A82038", ha="right",
               va="top")
    ax[0].text(adaptive[1]["mean_samples"], adaptive[1]["accuracy_all"] * 100,
               " sequential stopping", fontsize=11, color="#5E3F8C",
               va="bottom")
    ref4 = next(r for r in fixed if r["param"] == 4)
    asym = fixed[-1]["accuracy_all"] * 100
    ax[0].axhline(asym, color="grey", ls=":", lw=1.4)
    ax[0].text(1.05, asym, " asymptote of the fixed schedule", fontsize=9,
               color="grey", va="bottom")
    ax[0].set_xlabel("mean samples per decision")
    ax[0].set_ylabel("MNIST accuracy (%)")
    ax[0].set_title("Accuracy at equal sampling budget")
    ax[0].grid(alpha=0.3, which="both")

    b_show = 6
    hit = gap >= b_show
    stop = np.where(hit.any(0), hit.argmax(0), M_MAX - 1) + 1
    ax[1].hist(stop, bins=np.arange(0.5, stop.max() + 1.5),
               color="#5E3F8C", alpha=0.85)
    ax[1].set_xlim(b_show - 1.5, stop.max() + 1.5)
    ax[1].axvline(stop.mean(), color="#A82038", lw=2)
    ax[1].text(stop.mean(), ax[1].get_ylim()[1] * 0.9,
               f" mean {stop.mean():.1f}", color="#A82038", fontsize=11)
    ax[1].axvline(np.percentile(stop, 95), color="#1A6B5A", ls="--", lw=2)
    ax[1].text(np.percentile(stop, 95), ax[1].get_ylim()[1] * 0.6,
               f" 95th pct {np.percentile(stop, 95):.0f}", color="#1A6B5A",
               fontsize=11)
    ax[1].set_yscale("log")
    ax[1].set_xlabel(f"samples drawn before the vote margin reaches {b_show}")
    ax[1].set_ylabel("test images")
    ax[1].set_title("Per-input sampling cost")
    ax[1].grid(alpha=0.3, which="both")

    fig.tight_layout()
    out = REPO / "figures" / "38_conformal_sprt.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")
    print(f"total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
