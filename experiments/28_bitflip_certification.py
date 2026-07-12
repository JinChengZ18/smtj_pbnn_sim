"""28 -- Closed-form certification of bit-flip robustness (T1-2).

Experiment 09 measured the PBNN-vs-INT8 robustness gap empirically; this
experiment upgrades the PBNN side from "observed" to "certified":

  (a) BSC-contraction equivalence check: i.i.d. cell flips at rate p are
      EXACTLY equivalent to contracting every latent probability,
      q -> (1-2p) q + p (nn/certify.py). Two independent implementations
      -- explicit sign flips on drawn cells (experiment-09 style) vs the
      contracted-parameter evaluation -- must agree within binomial noise
      at every p.

  (b) Certified accuracy lower bound: per test sample, the probability of
      misclassification is bounded by the class-pair union of
      min(Bernstein, Gaussian+Berry-Esseen) tails of the last-layer
      margins, conditional on the binary features h; taking h draws from
      the corrupted network itself makes the bound end-to-end (law of
      total expectation), estimated over K feature draws with a CI.
      The bound uses the exact contracted mean -- NOT a zero-mean
      Hoeffding around the clean margin, which would be unsound.

  (c) BER specification inversion: the flip rate p* at which the
      certified lower bound (and, separately, the empirical accuracy)
      concedes 0.5 pp / 1 pp relative to p = 0, for T = 8 and T = 64.

Outputs:
  runs/28_bitflip_cert_<ts>/{certification.csv, summary.json}
  figures/28_bitflip_certification.png  (letter-free; deck adds letters)

Run from the repo root:  python experiments/28_bitflip_certification.py
"""

from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

T_GRID = (8, 64)
P_GRID = (0.0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30)
N_EVAL = 4000            # test subset; NOTE exp09 evaluates the full 10k set
K_H = 8                  # feature draws for the outer expectation over h
SEED = 42


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    import smtj_pbnn_sim.nn.pbnn_linear as pl
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.nn.certify import contract_p, per_sample_error_bound
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    set_global_seed(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("28_bitflip_cert", base=REPO / "runs")
    plt.rcParams.update({"font.family": "Arial", "font.size": 11})

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=250, num_workers=0)
    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    # scope assertions: the closed forms assume static per-cell Bernoulli
    # with no post-hoc clamp (clamp and contraction do not commute).
    # NOTE constructive, not detective: _device_params_from_cfg does not
    # parse these fields from the config, so the asserts document the
    # evaluation channel rather than validate the checkpoint config.
    assert dp.sigma_c2c == 0.0, "certify.py scope: no C2C noise channel"
    assert dp.p_max == 1.0, "certify.py scope: no p_max plateau clamp"

    def build(T):
        model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                         device_params=dp, variation_cfg=None,
                         T_full_stack=T).to(device)
        model.load_state_dict(state["model_state"], strict=True)
        calibrate_bn(model, train_loader, device,
                     mode=ForwardMode.FULL_STACK, T=T)
        return model

    def eval_subset(model, T) -> float:
        model.eval()                     # do not rely on calibrate_bn's state
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

    def with_flip_sampler(p_flip):
        """Experiment-09-style explicit sign flips on every drawn cell."""
        original = pl._bernoulli_pm1

        def flipped(p):
            w = original(p)
            if p_flip > 0:
                mask = (torch.rand_like(w) < p_flip).float()
                w = w * (1.0 - 2.0 * mask)
            return w
        return original, flipped

    def patch_contraction(layers, p_flip):
        for m in layers:
            orig = m.__class__._p_soft_for_sampling

            def p_soft(self, _o=orig, _pf=p_flip):
                return contract_p(_o(self), _pf)
            m._p_soft_for_sampling = types.MethodType(p_soft, m)

    def unpatch(layers):
        for m in layers:
            if "_p_soft_for_sampling" in m.__dict__:
                del m._p_soft_for_sampling

    rows = []
    fig, axes = plt.subplots(1, len(T_GRID), figsize=(11, 4.2), sharey=True)
    for ax, T in zip(np.atleast_1d(axes), T_GRID):
        model = build(T)
        layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]
        fc3 = layers[-1]
        # contracted q of the last layer is computed per p below; features h
        # are captured at fc3's input via a forward pre-hook
        h_buf = {}
        hook = fc3.register_forward_pre_hook(
            lambda mod, inp: h_buf.__setitem__("h", inp[0].detach()))

        emp_flip, emp_contr, cert_lb, cert_ci = [], [], [], []
        for p_f in P_GRID:
            # (a1) explicit-flip empirical accuracy
            orig, flipped = with_flip_sampler(p_f)
            pl._bernoulli_pm1 = flipped
            try:
                acc_flip = eval_subset(model, T)
            finally:
                pl._bernoulli_pm1 = orig
            # (a2) contracted-parameter empirical accuracy
            patch_contraction(layers, p_f)
            try:
                acc_contr = eval_subset(model, T)
                # (b) certified lower bound, h from the corrupted network
                with torch.no_grad():
                    # fc3 is already patched: _p_soft_for_sampling() returns
                    # the contracted q' -- use it directly (no double
                    # contraction)
                    q3 = fc3._p_soft_for_sampling()
                    bias = fc3.bias.detach() if fc3.bias is not None else None
                    lbs = []
                    for k in range(K_H):
                        torch.manual_seed(10_000 + 97 * k)
                        tot, n_done = 0.0, 0
                        for x, y in test_loader:
                            x, y = x.to(device), y.to(device)
                            model.forward_with_mode(
                                x, mode=ForwardMode.FULL_STACK, T=T)
                            h = torch.sign(h_buf["h"])
                            h = torch.where(h == 0, torch.ones_like(h), h)
                            eb = per_sample_error_bound(q3, h, y, bias, T)
                            tot += float((1.0 - eb).clamp_min(0).sum())
                            n_done += int(y.numel())
                            if n_done >= N_EVAL:
                                break
                        lbs.append(tot / n_done)
            finally:
                unpatch(layers)
            lb_m = float(np.mean(lbs))
            # one-sided 95% lower confidence limit over the K_H feature
            # draws (t_{0.95, df=7} = 1.895): the citable certified value is
            # the MC-estimated expectation bound with its LCL, not a
            # deterministic certificate (audit 2026-07-13)
            lb_ci = float(1.895 * np.std(lbs, ddof=1) / np.sqrt(K_H))
            emp_flip.append(acc_flip); emp_contr.append(acc_contr)
            cert_lb.append(lb_m); cert_ci.append(lb_ci)
            rows.append(dict(T=T, p_flip=p_f, acc_flip=round(acc_flip, 4),
                             acc_contracted=round(acc_contr, 4),
                             cert_lb=round(lb_m, 4),
                             cert_lcl95=round(lb_m - lb_ci, 4)))
            print(f"T={T:2d} p={p_f:4.2f}: flip {acc_flip:.4f} | "
                  f"contracted {acc_contr:.4f} | certified LB "
                  f"{lb_m:.4f}+-{lb_ci:.4f}")
        hook.remove()

        p = np.asarray(P_GRID)
        # binomial error bars on the single-run empirical points: the bound
        # constrains the POPULATION accuracy, so a tight bound legitimately
        # sits above an empirical point within its sampling noise
        eb_emp = [1.96 * np.sqrt(a * (1 - a) / N_EVAL) for a in emp_flip]
        ax.errorbar(p, emp_flip, yerr=eb_emp, fmt="o-", color="#5E3F8C",
                    label="empirical (explicit flips)", capsize=2)
        ax.plot(p, emp_contr, "s--", color="#1A6B5A",
                label="empirical (contracted params)")
        ax.errorbar(p, cert_lb, yerr=cert_ci, fmt="^-", color="#A82038",
                    label="certified lower bound")
        ax.set_xlabel("cell flip rate p")
        ax.set_title(f"T = {T} samples per weight")
        ax.grid(alpha=0.3)
    np.atleast_1d(axes)[0].set_ylabel("MNIST accuracy")
    np.atleast_1d(axes)[0].legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(REPO / "figures" / "28_bitflip_certification.png", dpi=300)
    print("figure saved: figures/28_bitflip_certification.png")

    # (c) BER inversion: p* where the curve concedes 0.5 pp / 1 pp vs p=0
    def invert(pgrid, curve, drop):
        c0 = curve[0]
        for i in range(1, len(curve)):
            if curve[i] <= c0 - drop:
                x0, x1 = pgrid[i - 1], pgrid[i]
                y0, y1 = curve[i - 1], curve[i]
                return x0 + (c0 - drop - y0) * (x1 - x0) / (y1 - y0)
        return float("nan")

    spec = {}
    for T in T_GRID:
        sub = [r for r in rows if r["T"] == T]
        for name, key in (("certified", "cert_lb"), ("empirical", "acc_flip")):
            curve = [r[key] for r in sub]
            spec[f"T{T}_{name}_p_at_0p5pp"] = invert(P_GRID, curve, 0.005)
            spec[f"T{T}_{name}_p_at_1pp"] = invert(P_GRID, curve, 0.010)
    print("\nBER specification (flip-rate budget):")
    for k, v in spec.items():
        print(f"  {k}: {v:.4f}" if v == v else f"  {k}: > {max(P_GRID)}")
    spec = {k: (v if v == v else None) for k, v in spec.items()}  # JSON-safe

    with open(run_dir / "certification.csv", "w", newline="",
              encoding="utf-8") as fc:
        w = csv.DictWriter(fc, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    (run_dir / "summary.json").write_text(json.dumps(dict(
        n_eval=N_EVAL, k_h=K_H, p_grid=list(P_GRID), t_grid=list(T_GRID),
        rows=rows, ber_spec=spec,
        scope=("bounds conditional on binary features drawn from the "
               "corrupted network (outer expectation over K_H draws, CI "
               "reported); tails = min(Bernstein, Gauss+Berry-Esseen 0.56); "
               "union over rival classes; exact contracted means -- no "
               "zero-mean-Hoeffding shortcut")), indent=1), encoding="utf-8")
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
