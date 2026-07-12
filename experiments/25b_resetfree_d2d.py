"""25b -- Read-then-set-polarity sampling under D2D mismatch (8-seed check).

Experiment 25 showed the read-then-set-polarity timing restores i.i.d.
sampling exactly when the conditional switching probabilities are realised
as programmed. Device-to-device variation breaks that exactness: the
programming voltages come from the NOMINAL calibration, so a cell whose
(V_th, V_T) deviates realises P(1|0) != P(1|1) -- the sample stream turns
weakly Markov again and its marginal is biased. This experiment quantifies
the accuracy cost across 8 D2D seeds and compares it against the
reset-then-program baseline carrying the SAME D2D write error (the standard
channel of experiment 08), i.e. it asks whether the correction's advantage
survives calibration mismatch.

Model: per-cell Delta_c = Delta (1 + cv z), cv = 0.077 (calibrated D2D),
mapped through the Neel-Brown forms used by device/variation.py:
V_th_c = V_c0 (1 - log_term / Delta_c), V_T_c = V_T Delta / Delta_c.
A cell programmed to target probability p then realises
logit(p_act) = a logit(p) + b with a = Delta_c/Delta,
b = (V_th_nom - V_th_c)/V_T_c. The same (a, b) is applied to both pulse
polarities (common-mode V_th shift; per-direction asymmetry is beyond this
first-order check). Per-slot relaxation mixing (g/2 per gap, from
experiment 25) is included before the read.

Outputs: runs/25b_resetfree_d2d_<ts>/accuracy.csv + summary.json

Run from the repo root:  python experiments/25b_resetfree_d2d.py
"""

from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

T = 4
N_EVAL = 2000
N_SEEDS = 8
CV_DELTA = 0.077
DELTA = 4.91
V_C0 = 0.857
V_TH = 0.895783
V_T = 0.023414
T_P, T_SLOT, TAU_0 = 0.75e-9, 4.0e-9, 1e-9


def main() -> None:
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("25b_resetfree_d2d", base=REPO / "runs")

    r0 = np.exp(-DELTA) / TAU_0
    g = 1.0 - np.exp(-2.0 * r0 * (T_SLOT - T_P))
    f_relax = float(g / 2.0)
    log_term = DELTA * (1.0 - V_TH / V_C0)

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=250, num_workers=0)
    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                     device_params=dp, variation_cfg=None,
                     T_full_stack=T).to(device)
    model.load_state_dict(state["model_state"], strict=True)
    calibrate_bn(model, train_loader, device, mode=ForwardMode.FULL_STACK, T=T)
    layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]

    def draw_ab(seed: int):
        """Per-layer (a, b) logit-transform tensors for one D2D realisation."""
        gen = torch.Generator(device="cpu").manual_seed(seed)
        ab = []
        for m in layers:
            shape = m.theta.shape
            z = torch.randn(shape, generator=gen).clamp_(-3, 3)
            delta_c = DELTA * (1.0 + CV_DELTA * z)
            vth_c = V_C0 * (1.0 - log_term / delta_c)
            vt_c = V_T * DELTA / delta_c
            a = (delta_c / DELTA).to(device)
            b = ((V_TH - vth_c) / vt_c).to(device)
            ab.append((a, b))
        return ab

    def make_fwd(scheme: str, a: "torch.Tensor", b: "torch.Tensor", seed: int):
        gen = torch.Generator(device=device).manual_seed(seed)

        def fwd(self, x, T_):
            with torch.no_grad():
                p = self._p_soft_for_sampling().clamp(1e-6, 1 - 1e-6)
                ell = torch.logit(p)
                q01 = torch.sigmoid(a * ell + b)                  # AP->P @ target p
                q10 = torch.sigmoid(a * torch.logit(1 - p) + b)   # P->AP @ target 1-p
                ws = []
                if scheme == "reset":
                    for _ in range(T_):
                        s = (torch.rand(p.shape, generator=gen,
                                        device=device) < q01).float()
                        ws.append(2.0 * s - 1.0)
                else:                                             # readset chain
                    if not hasattr(self, "_rs_state"):
                        pi = q01 / (q01 + q10).clamp_min(1e-9)
                        self._rs_state = (torch.rand(
                            p.shape, generator=gen, device=device) < pi).float()
                    s = self._rs_state
                    for _ in range(T_):
                        relax = torch.rand(s.shape, generator=gen,
                                           device=device) < f_relax
                        s = torch.where(relax, 1.0 - s, s)
                        q = torch.where(s > 0.5, 1.0 - q10, q01)
                        s = (torch.rand(s.shape, generator=gen,
                                        device=device) < q).float()
                        self._rs_state = s
                        ws.append(2.0 * s - 1.0)
            acc = None
            for w_ in ws:
                z_ = torch.nn.functional.linear(x, w_)
                acc = z_ if acc is None else acc + z_
            return acc / T_
        return fwd

    def eval_subset() -> float:
        n_done = n_ok = 0
        with torch.no_grad():
            for x, y in test_loader:
                x, y = x.to(device), y.to(device)
                logits = model.forward_with_mode(
                    x, mode=ForwardMode.FULL_STACK, T=T)
                n_ok += int((logits.argmax(1) == y).sum())
                n_done += int(y.numel())
                if n_done >= N_EVAL:
                    break
        return n_ok / n_done

    originals = [m._forward_full_stack for m in layers]
    rows = []
    for seed in range(N_SEEDS):
        ab = draw_ab(1000 + seed)
        accs = {}
        for scheme in ("readset", "reset"):
            for m, (a, b) in zip(layers, ab):
                m._forward_full_stack = types.MethodType(
                    make_fwd(scheme, a, b, seed=7000 + seed), m)
            accs[scheme] = eval_subset()
            for m, orig in zip(layers, originals):
                m._forward_full_stack = orig
                if hasattr(m, "_rs_state"):
                    del m._rs_state
        rows.append((seed, accs["readset"], accs["reset"]))
        print(f"seed {seed}: readset_d2d = {accs['readset']:.4f}   "
              f"reset_d2d = {accs['reset']:.4f}")

    rs = np.array([r[1] for r in rows])
    re_ = np.array([r[2] for r in rows])
    print(f"\nread-then-set under D2D: {rs.mean():.4f} +- {rs.std(ddof=1):.4f}")
    print(f"reset baseline under D2D: {re_.mean():.4f} +- {re_.std(ddof=1):.4f}")
    print(f"paired difference (readset - reset): "
          f"{(rs - re_).mean():+.4f} +- {(rs - re_).std(ddof=1):.4f}")
    print("(exp25 nominal, same subset: readset 0.9645, reset 0.9660)")

    with open(run_dir / "accuracy.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.writer(fc)
        w.writerow(["seed", "readset_d2d", "reset_d2d"])
        for r in rows:
            w.writerow([r[0], round(r[1], 4), round(r[2], 4)])
    (run_dir / "summary.json").write_text(json.dumps(dict(
        n_seeds=N_SEEDS, n_eval=N_EVAL, T=T, cv_delta=CV_DELTA,
        readset_mean=float(rs.mean()), readset_sd=float(rs.std(ddof=1)),
        reset_mean=float(re_.mean()), reset_sd=float(re_.std(ddof=1)),
        paired_diff_mean=float((rs - re_).mean()),
        paired_diff_sd=float((rs - re_).std(ddof=1)),
        note=("common-mode V_th shift applied to both pulse polarities; "
              "per-direction asymmetry beyond this first-order check")),
        indent=1), encoding="utf-8")
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
