"""26 -- Native uncertainty quantification from the PBNN sampling budget.

The stochastic forward already draws Bernoulli samples per inference; this
experiment consumes those SAME samples as an ensemble (Gal-Ghahramani
decomposition, ``train/uncertainty.py``) instead of only averaging them,
and asks what calibration, selective-prediction and OOD-detection quality
each sampling depth M buys -- the M-resolved UQ-quality-vs-energy frontier.
No additional circuitry or entropy source is involved: every quantity is
computed from the M single-sample forwards the inference would run anyway.

Measured quantities per M in {2,4,8,16,32,64} on the full MNIST test set:

  * accuracy of the M-sample mean prediction
  * expected calibration error (ECE, 15 bins, confidence = max mean prob)
  * selective prediction: accuracy at 90% coverage, ranked by predictive
    entropy (total uncertainty)
  * OOD detection: AUROC MNIST-test vs Fashion-MNIST-test, scored by
    mutual information (epistemic) and by predictive entropy

Baselines: the deterministic FP-NN and BNN (exp23-trained instances),
scored by softmax confidence/entropy -- single pass, no ensemble axis.

Energy axis: per-decision energy = M x (per-MAC energy x MAC count),
with the sky130-grounded per-MAC constants (Table 4.6 caliber).

Outputs:
  runs/26_native_uq_<ts>/uq_frontier.csv
  figures/26_native_uq.png

Run from the repo root:

    python experiments/26_native_uq.py
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

_spec = importlib.util.spec_from_file_location(
    "exp07", REPO / "experiments" / "07_baseline_comparison.py")
exp07 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exp07)

M_GRID = [2, 4, 8, 16, 32, 64]
COVERAGE = 0.90
N_BINS = 15


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.data.fashion_mnist import get_fashion_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.train.uncertainty import predictive_uncertainty
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.ppa.tech_params import default_28nm
    from smtj_pbnn_sim.ppa.energy import per_mac_energy

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("26_native_uq", base=REPO / "runs")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=500, num_workers=0)
    _, ood_loader = get_fashion_mnist_loaders(
        root="./data/fashion_mnist", batch_size=500, num_workers=0)

    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                     device_params=dp, variation_cfg=None,
                     T_full_stack=1).to(device)        # 1-sample ensemble members
    model.load_state_dict(state["model_state"], strict=True)
    calibrate_bn(model, train_loader, device,
                 mode=ForwardMode.FULL_STACK, T=1)

    def collect(loader, M):
        """Mean probs + uncertainties over a whole loader."""
        outs = {"probs": [], "pe": [], "mi": [], "y": []}
        for x, y in loader:
            x = x.to(device)
            u = predictive_uncertainty(model, x, M, mode=ForwardMode.FULL_STACK)
            outs["probs"].append(u["mean_probs"].cpu())
            outs["pe"].append(u["predictive_entropy"].cpu())
            outs["mi"].append(u["mutual_information"].cpu())
            outs["y"].append(y)
        return {k: torch.cat(v) for k, v in outs.items()}

    def ece(conf, correct):
        edges = np.linspace(0, 1, N_BINS + 1)
        e = 0.0
        for i in range(N_BINS):
            m = (conf > edges[i]) & (conf <= edges[i + 1])
            if m.sum() == 0:
                continue
            e += m.mean() * abs(correct[m].mean() - conf[m].mean())
        return float(e)

    def auroc(neg, pos):
        """AUROC for pos (OOD) scored above neg (ID); rank-based."""
        s = np.concatenate([neg, pos])
        r = s.argsort().argsort().astype(np.float64) + 1
        n_p, n_n = len(pos), len(neg)
        return float((r[n_n:].sum() - n_p * (n_p + 1) / 2) / (n_p * n_n))

    tech = default_28nm()
    macs = 784 * 1024 + 1024 * 1024 + 1024 * 10
    e_mac = per_mac_energy(tech)

    rows = []
    for M in M_GRID:
        idd = collect(test_loader, M)
        ood = collect(ood_loader, M)
        y = idd["y"].numpy()
        probs = idd["probs"].numpy()
        pred = probs.argmax(1)
        correct = (pred == y).astype(np.float64)
        conf = probs.max(1)
        acc = correct.mean()
        e_cal = ece(conf, correct)
        # selective prediction at fixed coverage, ranked by predictive entropy
        order = np.argsort(idd["pe"].numpy())
        keep = order[: int(COVERAGE * len(order))]
        acc_sel = correct[keep].mean()
        au_mi = auroc(idd["mi"].numpy(), ood["mi"].numpy())
        au_pe = auroc(idd["pe"].numpy(), ood["pe"].numpy())
        e_dec = M * macs * e_mac
        rows.append({"model": "pbnn", "M": M, "accuracy": round(float(acc), 4),
                     "ece": round(e_cal, 4),
                     "acc_at_90cov": round(float(acc_sel), 4),
                     "auroc_mi": round(au_mi, 4), "auroc_pe": round(au_pe, 4),
                     "energy_uJ": round(e_dec * 1e6, 3)})
        print(f"PBNN M={M:2d}: acc={acc:.4f} ECE={e_cal:.4f} "
              f"acc@90%cov={acc_sel:.4f} AUROC(MI)={au_mi:.4f} "
              f"AUROC(PE)={au_pe:.4f} E={e_dec*1e6:.2f} uJ")

    # deterministic baselines from the exp23-trained instances
    exp23_dirs = sorted((REPO / "runs").glob("23_eot_attack_*"))
    BNN_MLP, FP_MLP = exp07._make_models(hidden=1024)
    for name, cls, fn in (("bnn", BNN_MLP, "BNN_state.pt"),
                          ("fp", FP_MLP, "FP_state.pt")):
        net = cls(hidden=1024).to(device)
        net.load_state_dict(torch.load(exp23_dirs[-1] / fn,
                                       map_location=device))
        net.eval()

        def one_pass(loader):
            ps, ys = [], []
            with torch.no_grad():
                for x, y in loader:
                    ps.append(torch.softmax(net(x.to(device)), -1).cpu())
                    ys.append(y)
            return torch.cat(ps).numpy(), torch.cat(ys).numpy()

        p_id, y_id = one_pass(test_loader)
        p_ood, _ = one_pass(ood_loader)
        correct = (p_id.argmax(1) == y_id).astype(np.float64)
        conf = p_id.max(1)
        ent_id = -(np.clip(p_id, 1e-12, 1) * np.log(np.clip(p_id, 1e-12, 1))).sum(1)
        ent_ood = -(np.clip(p_ood, 1e-12, 1) * np.log(np.clip(p_ood, 1e-12, 1))).sum(1)
        order = np.argsort(ent_id)
        keep = order[: int(COVERAGE * len(order))]
        rows.append({"model": name, "M": 1,
                     "accuracy": round(float(correct.mean()), 4),
                     "ece": round(ece(conf, correct), 4),
                     "acc_at_90cov": round(float(correct[keep].mean()), 4),
                     "auroc_mi": "", "auroc_pe": round(auroc(ent_id, ent_ood), 4),
                     "energy_uJ": ""})
        print(f"{name.upper():4s} softmax: acc={correct.mean():.4f} "
              f"ECE={ece(conf, correct):.4f} "
              f"acc@90%cov={correct[keep].mean():.4f} "
              f"AUROC(entropy)={auroc(ent_id, ent_ood):.4f}")

    with open(run_dir / "uq_frontier.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"CSV written to {run_dir}")

    # ----- figure -----------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    pb = [r for r in rows if r["model"] == "pbnn"]
    fp = next(r for r in rows if r["model"] == "fp")
    bnn = next(r for r in rows if r["model"] == "bnn")
    E = [r["energy_uJ"] for r in pb]
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.8))

    ax[0].semilogx(E, [r["ece"] for r in pb], "o-", color="#5E3F8C", lw=2)
    ax[0].axhline(fp["ece"], color="#A82038", ls="--", lw=1.6)
    ax[0].axhline(bnn["ece"], color="#1A6B5A", ls=":", lw=1.6)
    ax[0].text(E[0], fp["ece"], " FP-NN softmax", fontsize=10, va="bottom",
               color="#A82038")
    ax[0].text(E[0], bnn["ece"], " BNN softmax", fontsize=10, va="bottom",
               color="#1A6B5A")
    ax[0].set_xlabel("energy per decision (uJ)")
    ax[0].set_ylabel("expected calibration error")
    ax[0].set_title("Calibration vs sampling energy")
    ax[0].grid(alpha=0.3, which="both")

    ax[1].semilogx(E, [r["auroc_mi"] for r in pb], "o-", color="#5E3F8C",
                   lw=2, label="mutual information (epistemic)")
    ax[1].semilogx(E, [r["auroc_pe"] for r in pb], "s--", color="#9580BD",
                   lw=2, label="predictive entropy (total)")
    ax[1].axhline(fp["auroc_pe"], color="#A82038", ls="--", lw=1.6)
    ax[1].text(E[0], fp["auroc_pe"], " FP-NN entropy", fontsize=10,
               va="bottom", color="#A82038")
    ax[1].set_xlabel("energy per decision (uJ)")
    ax[1].set_ylabel("OOD AUROC (Fashion-MNIST)")
    ax[1].set_title("OOD detection vs sampling energy")
    ax[1].legend(fontsize=9); ax[1].grid(alpha=0.3, which="both")

    ax[2].semilogx(E, [r["accuracy"] * 100 for r in pb], "o-",
                   color="#5E3F8C", lw=2, label="full coverage")
    ax[2].semilogx(E, [r["acc_at_90cov"] * 100 for r in pb], "s--",
                   color="#1A6B5A", lw=2, label="90% coverage (entropy-ranked)")
    ax[2].set_xlabel("energy per decision (uJ)")
    ax[2].set_ylabel("MNIST accuracy (%)")
    ax[2].set_title("Selective prediction from the same samples")
    ax[2].legend(fontsize=9); ax[2].grid(alpha=0.3, which="both")

    fig.tight_layout()
    out = REPO / "figures" / "26_native_uq.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
