"""37 -- Does the native-UQ epistemic signal revive on a harder task?

Experiment 26 found the honest negative on MNIST: the mutual-information
(epistemic) OOD score DEGRADES with sampling depth M, because the
theta x100 post-scaled MNIST checkpoint is almost fully saturated --
sigmoid(theta) sits at 0 or 1 for most cells, so the M members of the
"ensemble" barely disagree and averaging only removes the little
disagreement that exists. The pre-registered follow-up asked whether a
harder dataset, where the network cannot saturate its way to the answer,
restores the epistemic axis.

This experiment reruns the exp-26 protocol on the CIFAR-10 PBNN-CNN
checkpoint (experiment 05a) with three evaluation sets:

  * in-distribution: CIFAR-10 test
  * distribution shift: the same images under CIFAR-10-C style Gaussian
    noise and defocus blur (self-generated, fixed severity)
  * far OOD: Fashion-MNIST upsampled to 32x32 and replicated to 3
    channels (a deliberately easy far-OOD control)

and reports, per M in {2,4,8,16,32,64}: accuracy, ECE, selective-
prediction accuracy at 90% coverage, and detection AUROC by mutual
information (epistemic) and predictive entropy (total).

The mechanistic cross-check is the per-cell probability histogram
p = sigmoid(theta) for the MNIST MLP and the CIFAR-10 CNN checkpoints:
if the saturation explanation is right, the CIFAR model must keep a
substantially larger mid-range population.

Outputs:
  runs/37_cifar_uq_<ts>/cifar_uq.csv
  runs/37_cifar_uq_<ts>/saturation.csv
  figures/37_cifar_uq.png

Run from the repo root (needs runs/cifar10_pbnn_cnn/best.pt from 05a and
runs/mnist_pbnn_mlp/best.pt for the saturation contrast):

    python experiments/37_cifar_uq.py
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
    "exp06a", REPO / "experiments" / "06a_cifar10_sweep_T_vs_accuracy.py")
exp06a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exp06a)

M_GRID = [2, 4, 8, 16, 32, 64]
COVERAGE = 0.90
N_BINS = 15
N_EVAL = 2000          # images per evaluation set (CNN forwards are costly)
NOISE_SIGMA = 0.10     # CIFAR-10-C "gaussian_noise" severity 3 caliber
BLUR_SIGMA = 1.0       # defocus/blur proxy, pixel units


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch
    import torch.nn.functional as F

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode
    from smtj_pbnn_sim.data.cifar import (CIFAR10Parquet, CIFAR10_MEAN,
                                          CIFAR10_STD, get_cifar10_loaders)
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.train.uncertainty import predictive_uncertainty
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    t0 = time.time()
    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("37_cifar_uq", base=REPO / "runs")
    print(f"device: {device}")

    ckpt = REPO / "runs" / "cifar10_pbnn_cnn" / "best.pt"
    if not ckpt.exists():
        print(f"checkpoint not found: {ckpt} (run experiments/05a first)")
        sys.exit(1)
    state = torch.load(ckpt, map_location="cpu")
    cfg = state["config"]
    dp = exp06a._device_params_from_ckpt(cfg)
    mc = cfg.get("model", {})
    base_ch = int(mc.get("base_ch", 64))
    hidden_fc = int(mc.get("hidden_fc", 1024))
    num_classes = int(mc.get("num_classes", 10))

    PBNN_CNN = exp06a._make_pbnn_cnn(
        base_ch=base_ch, hidden_fc=hidden_fc, num_classes=num_classes,
        device_params=dp, T_full_stack=1)
    model = PBNN_CNN().to(device)
    model.load_state_dict(state["model_state"], strict=True)
    for m in model.modules():                    # 1-sample ensemble members
        if hasattr(m, "T_full_stack"):
            m.T_full_stack = 1

    train_loader, _ = get_cifar10_loaders(root="./data/cifar10",
                                          batch_size=128, num_workers=0,
                                          augment=False)
    calibrate_bn(model, train_loader, device, mode=ForwardMode.FULL_STACK, T=1)

    # ---- evaluation sets (raw [0,1] tensors, corruption before normalisation)
    from torchvision import transforms
    raw = CIFAR10Parquet(root=Path("./data/cifar10"), train=False,
                         transform=transforms.ToTensor())
    xs = torch.stack([raw[i][0] for i in range(N_EVAL)])
    ys = torch.tensor([raw[i][1] for i in range(N_EVAL)])
    mean = torch.tensor(CIFAR10_MEAN).view(1, 3, 1, 1)
    std = torch.tensor(CIFAR10_STD).view(1, 3, 1, 1)

    def norm(t):
        return (t - mean) / std

    def gaussian_blur(t, sigma):
        r = int(3 * sigma) | 1
        g = torch.exp(-(torch.arange(-r, r + 1, dtype=torch.float32) ** 2)
                      / (2 * sigma ** 2))
        g = (g / g.sum()).view(1, 1, -1)
        k = t.reshape(-1, 1, t.shape[-2], t.shape[-1])
        k = F.conv2d(F.pad(k, (r, r, 0, 0), mode="reflect"), g.view(1, 1, 1, -1))
        k = F.conv2d(F.pad(k, (0, 0, r, r), mode="reflect"), g.view(1, 1, -1, 1))
        return k.reshape(t.shape)

    gen = torch.Generator().manual_seed(7)
    x_id = norm(xs)
    x_noise = norm((xs + NOISE_SIGMA * torch.randn(xs.shape, generator=gen))
                   .clamp(0, 1))
    x_blur = norm(gaussian_blur(xs, BLUR_SIGMA))

    from torchvision.datasets import FashionMNIST
    fm = FashionMNIST(root="./data/fashion_mnist", train=False, download=False,
                      transform=transforms.ToTensor())
    fx = torch.stack([fm[i][0] for i in range(N_EVAL)])
    fx = F.interpolate(fx, size=32, mode="bilinear",
                       align_corners=False).repeat(1, 3, 1, 1)
    x_ood = norm(fx)

    # ---- metrics -----------------------------------------------------------
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
        s = np.concatenate([neg, pos])
        r = s.argsort().argsort().astype(np.float64) + 1
        n_p, n_n = len(pos), len(neg)
        return float((r[n_n:].sum() - n_p * (n_p + 1) / 2) / (n_p * n_n))

    def collect(x, M, bs=250):
        out = {"probs": [], "pe": [], "mi": []}
        for i in range(0, len(x), bs):
            u = predictive_uncertainty(model, x[i:i + bs].to(device), M,
                                       mode=ForwardMode.FULL_STACK)
            out["probs"].append(u["mean_probs"].cpu())
            out["pe"].append(u["predictive_entropy"].cpu())
            out["mi"].append(u["mutual_information"].cpu())
        return {k: torch.cat(v).numpy() for k, v in out.items()}

    @torch.no_grad()
    def acc_inlayer(M, bs=250):
        """Accuracy when the SAME M samples are averaged inside the layers
        (T_full_stack = M, one pass) instead of across M outer members."""
        net = PBNN_CNN().to(device)
        net.load_state_dict(state["model_state"], strict=True)
        for mod in net.modules():
            if hasattr(mod, "T_full_stack"):
                mod.T_full_stack = M
        calibrate_bn(net, train_loader, device,
                     mode=ForwardMode.FULL_STACK, T=M)
        net.eval()
        hit = 0
        for i in range(0, len(x_id), bs):
            lg = net.forward_with_mode(x_id[i:i + bs].to(device),
                                       mode=ForwardMode.FULL_STACK, T=M)
            hit += (lg.argmax(1).cpu() == ys[i:i + bs]).sum().item()
        return hit / len(x_id)

    rows = []
    for M in M_GRID:
        idd = collect(x_id, M)
        noi = collect(x_noise, M)
        blr = collect(x_blur, M)
        ood = collect(x_ood, M)
        pred = idd["probs"].argmax(1)
        correct = (pred == ys.numpy()).astype(np.float64)
        conf = idd["probs"].max(1)
        order = np.argsort(idd["pe"])
        keep = order[: int(COVERAGE * len(order))]
        row = {
            "M": M, "n_eval": N_EVAL,
            "accuracy": round(float(correct.mean()), 4),
            "acc_inlayer_T": round(acc_inlayer(M), 4),
            "ece": round(ece(conf, correct), 4),
            "acc_at_90cov": round(float(correct[keep].mean()), 4),
            "auroc_mi_noise": round(auroc(idd["mi"], noi["mi"]), 4),
            "auroc_pe_noise": round(auroc(idd["pe"], noi["pe"]), 4),
            "auroc_mi_blur": round(auroc(idd["mi"], blr["mi"]), 4),
            "auroc_pe_blur": round(auroc(idd["pe"], blr["pe"]), 4),
            "auroc_mi_ood": round(auroc(idd["mi"], ood["mi"]), 4),
            "auroc_pe_ood": round(auroc(idd["pe"], ood["pe"]), 4),
        }
        rows.append(row)
        print(f"M={M:2d}: acc={row['accuracy']:.4f} ECE={row['ece']:.4f} "
              f"acc@90={row['acc_at_90cov']:.4f} | AUROC(MI) "
              f"noise={row['auroc_mi_noise']:.3f} blur={row['auroc_mi_blur']:.3f} "
              f"ood={row['auroc_mi_ood']:.3f} | AUROC(PE) "
              f"noise={row['auroc_pe_noise']:.3f} ood={row['auroc_pe_ood']:.3f} "
              f"({time.time()-t0:.0f}s)", flush=True)
        with open(run_dir / "cifar_uq.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)

    # ---- saturation contrast ----------------------------------------------
    def theta_probs(sd):
        th = [v.flatten() for k, v in sd.items() if k.endswith("theta")]
        return torch.sigmoid(torch.cat(th)).numpy() if th else np.array([])

    sat_rows, hists = [], {}
    for name, path in (("cifar10_cnn", ckpt),
                       ("mnist_mlp", REPO / "runs" / "mnist_pbnn_mlp" / "best.pt")):
        if not path.exists():
            continue
        sd = torch.load(path, map_location="cpu")["model_state"]
        p = theta_probs(sd)
        if p.size == 0:
            continue
        hists[name] = p
        mid = float(((p >= 0.2) & (p <= 0.8)).mean())
        sat = float(((p < 0.01) | (p > 0.99)).mean())
        sat_rows.append({"model": name, "n_cells": int(p.size),
                         "frac_mid_0p2_0p8": round(mid, 4),
                         "frac_saturated": round(sat, 4)})
        print(f"{name}: mid-range p in [0.2,0.8] = {mid*100:.1f}%, "
              f"saturated (<1% or >99%) = {sat*100:.1f}%  ({p.size} cells)")
    with open(run_dir / "saturation.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sat_rows[0]))
        w.writeheader(); w.writerows(sat_rows)
    print(f"CSV written to {run_dir}")

    # ---- figure ------------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.8))
    Ms = [r["M"] for r in rows]

    ax[0].semilogx(Ms, [r["auroc_mi_noise"] for r in rows], "o-",
                   color="#5E3F8C", lw=2, base=2)
    ax[0].semilogx(Ms, [r["auroc_mi_blur"] for r in rows], "s-",
                   color="#9580BD", lw=2, base=2)
    ax[0].semilogx(Ms, [r["auroc_mi_ood"] for r in rows], "^-",
                   color="#1A6B5A", lw=2, base=2)
    mn = REPO / "runs" / "26_native_uq_20260708_070501" / "uq_frontier.csv"
    if mn.exists():
        with open(mn, encoding="utf-8") as f:
            pb = [r for r in csv.DictReader(f) if r["model"] == "pbnn"]
        ax[0].semilogx([int(r["M"]) for r in pb],
                       [float(r["auroc_mi"]) for r in pb], "v--",
                       color="#A82038", lw=2, base=2)
        ax[0].text(Ms[0], float(pb[0]["auroc_mi"]),
                   " MNIST MLP, Fashion-MNIST", fontsize=9, color="#A82038",
                   va="top")
    ax[0].text(Ms[0], rows[0]["auroc_mi_noise"], " CIFAR-10, gaussian noise",
               fontsize=9, color="#5E3F8C", va="bottom")
    ax[0].text(Ms[0], rows[0]["auroc_mi_blur"], " CIFAR-10, blur",
               fontsize=9, color="#9580BD", va="top")
    ax[0].text(Ms[0], rows[0]["auroc_mi_ood"], " CIFAR-10, Fashion-MNIST",
               fontsize=9, color="#1A6B5A", va="bottom")
    ax[0].set_xlabel("sampling depth M")
    ax[0].set_ylabel("detection AUROC (mutual information)")
    ax[0].set_title("Epistemic signal vs sampling depth")
    ax[0].grid(alpha=0.3, which="both")

    ax[1].semilogx(Ms, [r["ece"] for r in rows], "o-", color="#5E3F8C",
                   lw=2, base=2, label="ECE")
    ax[1].set_xlabel("sampling depth M")
    ax[1].set_ylabel("expected calibration error")
    ax[1].set_title("Calibration on CIFAR-10")
    ax[1].grid(alpha=0.3, which="both")
    ax1b = ax[1].twinx()
    ax1b.semilogx(Ms, [r["accuracy"] * 100 for r in rows], "s--",
                  color="#1A6B5A", lw=2, base=2)
    ax1b.semilogx(Ms, [r["acc_at_90cov"] * 100 for r in rows], "^:",
                  color="#A82038", lw=2, base=2)
    ax1b.set_ylabel("accuracy (%)")
    ax1b.text(Ms[-1], rows[-1]["accuracy"] * 100, "full coverage ",
              fontsize=9, color="#1A6B5A", ha="right", va="top")
    ax1b.text(Ms[-1], rows[-1]["acc_at_90cov"] * 100, "90% coverage ",
              fontsize=9, color="#A82038", ha="right", va="bottom")

    for name, color in (("mnist_mlp", "#A82038"), ("cifar10_cnn", "#5E3F8C")):
        if name in hists:
            ax[2].hist(hists[name], bins=50, histtype="step", lw=2,
                       density=True, color=color,
                       label="MNIST MLP" if name == "mnist_mlp"
                       else "CIFAR-10 CNN")
    ax[2].set_yscale("log")
    ax[2].set_xlabel(r"per-cell write probability $\sigma(\theta)$")
    ax[2].set_ylabel("density")
    ax[2].set_title("Latent saturation of the two checkpoints")
    ax[2].legend(fontsize=9)
    ax[2].grid(alpha=0.3, which="both")

    fig.tight_layout()
    out = REPO / "figures" / "37_cifar_uq.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")
    print(f"total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
