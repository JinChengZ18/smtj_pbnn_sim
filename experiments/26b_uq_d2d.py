"""26b -- Does device-instance (D2D) ensembling revive the OOD signal?

Experiment 26 found the honest negative: M-sample ensembling of one PBNN
device instance IMPROVES calibration but DEGRADES mutual-information OOD
detection (averaging suppresses epistemic disagreement on a theta-saturated
checkpoint). The pre-registered follow-up probes whether epistemic diversity
returns when the ensemble members are DIFFERENT device realisations: each
member m redraws the calibrated D2D field (Delta_c = Delta (1 + 0.077 z),
mapped to per-cell logit transform a ell + b as in experiment 25b), i.e. a
chip-ensemble / reprogramming-noise reading of the same hardware.

For each M in {4, 16, 64}: members are paired across ID (MNIST test) and
OOD (Fashion-MNIST) loaders (same device field on both), T=1 full-stack
forward per member; metrics = ECE / accuracy on ID, AUROC (MI and PE) for
OOD; the no-D2D variant (a=1, b=0, sampling stochasticity only) is measured
in the same run as the paired baseline.

Outputs: runs/26b_uq_d2d_<ts>/summary.csv + summary.json

Run from the repo root:  python experiments/26b_uq_d2d.py
"""

from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

M_GRID = (4, 16, 64)
N_EVAL = 4000                 # per-loader image subset (AUROC/ECE stable)
N_BINS = 15
CV_DELTA = 0.077
DELTA = 4.91
V_C0 = 0.857
V_TH = 0.895783
V_T = 0.023414


def main() -> None:
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.data.fashion_mnist import get_fashion_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("26b_uq_d2d", base=REPO / "runs")

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=250, num_workers=0)
    _, ood_loader = get_fashion_mnist_loaders(
        root="./data/fashion_mnist", batch_size=250, num_workers=0)
    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                     device_params=dp, variation_cfg=None,
                     T_full_stack=1).to(device)
    model.load_state_dict(state["model_state"], strict=True)
    calibrate_bn(model, train_loader, device, mode=ForwardMode.FULL_STACK, T=1)
    layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]
    log_term = DELTA * (1.0 - V_TH / V_C0)

    def patch_d2d(seed: int):
        """Monkeypatch every layer's p_soft with one D2D realisation."""
        gen = torch.Generator(device="cpu").manual_seed(seed)
        for m in layers:
            z = torch.randn(m.theta.shape, generator=gen).clamp_(-3, 3)
            delta_c = DELTA * (1.0 + CV_DELTA * z)
            vth_c = V_C0 * (1.0 - log_term / delta_c)
            vt_c = V_T * DELTA / delta_c
            a = (delta_c / DELTA).to(device)
            b = ((V_TH - vth_c) / vt_c).to(device)
            orig = m.__class__._p_soft_for_sampling

            def p_soft(self, _a=a, _b=b, _orig=orig):
                p = _orig(self).clamp(1e-6, 1 - 1e-6)
                return torch.sigmoid(_a * torch.logit(p) + _b)
            m._p_soft_for_sampling = types.MethodType(p_soft, m)

    def unpatch():
        for m in layers:
            if "_p_soft_for_sampling" in m.__dict__:
                del m._p_soft_for_sampling

    @torch.no_grad()
    def member_probs(loader):
        """One T=1 full-stack pass -> softmax probs on the first N_EVAL images."""
        chunks, ys, n = [], [], 0
        for x, y in loader:
            x = x.to(device)
            logits = model.forward_with_mode(x, mode=ForwardMode.FULL_STACK, T=1)
            chunks.append(torch.softmax(logits, 1).cpu())
            ys.append(y)
            n += int(y.numel())
            if n >= N_EVAL:
                break
        return torch.cat(chunks)[:N_EVAL], torch.cat(ys)[:N_EVAL]

    def ece(conf, correct):
        edges = np.linspace(0, 1, N_BINS + 1)
        e = 0.0
        for i in range(N_BINS):
            msk = (conf > edges[i]) & (conf <= edges[i + 1])
            if msk.sum() == 0:
                continue
            e += msk.mean() * abs(correct[msk].mean() - conf[msk].mean())
        return float(e)

    def auroc(neg, pos):
        s = np.concatenate([neg, pos])
        r = s.argsort().argsort().astype(np.float64) + 1
        n_p, n_n = len(pos), len(neg)
        return float((r[n_n:].sum() - n_p * (n_p + 1) / 2) / (n_p * n_n))

    def uq(prob_stack):
        """prob_stack [M, N, C] -> mean probs, predictive entropy, MI."""
        mean_p = prob_stack.mean(0)
        pe = -(mean_p.clamp_min(1e-12) * mean_p.clamp_min(1e-12).log()).sum(1)
        h_m = -(prob_stack.clamp_min(1e-12)
                * prob_stack.clamp_min(1e-12).log()).sum(2).mean(0)
        return mean_p, pe, pe - h_m

    rows = []
    for variant in ("d2d_ensemble", "nominal"):
        for M in M_GRID:
            id_stack, ood_stack, y_id = [], [], None
            for m_i in range(M):
                if variant == "d2d_ensemble":
                    patch_d2d(seed=5000 + m_i)
                p_id, y_id = member_probs(test_loader)
                p_ood, _ = member_probs(ood_loader)
                unpatch()
                id_stack.append(p_id)
                ood_stack.append(p_ood)
            id_s = torch.stack(id_stack)
            ood_s = torch.stack(ood_stack)
            mp_id, pe_id, mi_id = uq(id_s)
            _, pe_ood, mi_ood = uq(ood_s)
            pred = mp_id.argmax(1).numpy()
            correct = (pred == y_id.numpy()).astype(np.float64)
            conf = mp_id.max(1).values.numpy()
            row = dict(variant=variant, M=M,
                       acc=float(correct.mean()),
                       ece=ece(conf, correct),
                       auroc_mi=auroc(mi_id.numpy(), mi_ood.numpy()),
                       auroc_pe=auroc(pe_id.numpy(), pe_ood.numpy()))
            rows.append(row)
            print("{variant:13s} M={M:2d}: acc={acc:.4f} ece={ece:.4f} "
                  "AUROC(MI)={auroc_mi:.3f} AUROC(PE)={auroc_pe:.3f}"
                  .format(**row))

    with open(run_dir / "summary.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.DictWriter(fc, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (run_dir / "summary.json").write_text(
        json.dumps(dict(n_eval=N_EVAL, cv_delta=CV_DELTA, rows=rows), indent=1),
        encoding="utf-8")
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
