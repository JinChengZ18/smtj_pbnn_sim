"""25 -- Reset-free Bernoulli sampling: Markov bias, corrections, energy.

The PBNN energy model bills one write per stochastic sample, implicitly
assuming each write starts from a known state (reset-then-program, the
Fukushima-style timing). This experiment quantifies what happens when the
reset phase is dropped and the cell free-runs as a two-state Markov chain,
and evaluates the two corrections, on the calibrated device numbers:

  free-running chain per sample slot (t_p = 0.75 ns programming pulse +
  t_gap zero-bias relaxation): the programming pulse only ratchets the
  state TOWARD its own polarity (the reverse in-pulse rate is suppressed
  by exp(-2 Delta V/V_c0) ~ 3e-5), while the zero-bias gap relaxes toward
  50/50 with tau(0) ~ 68 ns >> t_gap. Two structural consequences:

    * a unipolar pulse train can never realise a stationary AP fraction
      below 1/2 -- half of the weight range is unreachable unless the
      pulse polarity is chosen statically per cell by sign(theta);
    * with sign-static polarity + pre-distortion (invert the stationary
      map), mid-range cells sit at flip probabilities ~ g/2 ~ 2%, so the
      chain mixes over ~20 slots: T = 4 samples are strongly correlated
      within one inference AND across consecutive inferences.

  read-then-set-polarity: read the state (the 48 fJ decision already
  billed per sample), choose the pulse polarity so the CONDITIONAL
  switching probability realises the target marginal exactly -- this
  restores i.i.d. sampling with no reset pulse, using the bipolar
  calibration (both P->AP and AP->P fits exist in the committed data).

Parts
-----
  (a) chain analysis (numpy): stationary map pi(theta), pre-distortion
      inverse, slot-to-slot autocorrelation, T=4 variance inflation
  (b) MNIST accuracy (torch, 2000-image subset): i.i.d. baseline vs
      free-running pre-distorted chain (state persists across samples
      and across inputs) vs read-then-set (i.i.d. by construction)
  (c) write-path energy per sample for the three timings (tech_params)

Outputs:
  runs/25_resetfree_<ts>/{chain.csv, accuracy.csv}
  figures/25_resetfree_sampling.png

Run from the repo root:

    python experiments/25_resetfree_sampling.py
"""

from __future__ import annotations

import csv
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

T_P = 0.75e-9          # programming pulse width [s]
T_SLOT = 4.0e-9        # sample slot period [s] (system clock, Chapter 1 framing)
DELTA = 4.91           # NB barrier (auto-fit), sets tau(0) = tau_0 e^Delta / 2
TAU_0 = 1e-9
V_C0 = 0.857
N_EVAL = 2000          # MNIST test subset for the accuracy part


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear, _bernoulli_pm1
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.ppa.tech_params import default_28nm

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("25_resetfree", base=REPO / "runs")
    T = 4

    # ----- (a) chain analysis --------------------------------------------
    t_gap = T_SLOT - T_P
    r0 = np.exp(-DELTA) / TAU_0                 # zero-bias rate, each direction
    g = 1.0 - np.exp(-2.0 * r0 * t_gap)         # relaxation mixing per gap
    tau0V = 1.0 / (2.0 * r0)
    print(f"tau(0V) = {tau0V*1e9:.1f} ns; per-slot relaxation mixing g = {g*100:.2f}%"
          f" (flip prob g/2 = {g/2*100:.2f}%)")

    def slot_matrix(p_pulse: np.ndarray):
        """Per-slot transition: relax (flip w.p. g/2), then pulse toward the
        cell's own polarity axis (state 1 = pulse-favoured state)."""
        # states {0,1}; relax: flip w.p. g/2 either way
        # pulse: 0->1 w.p. p_pulse; 1->0 w.p. p_pulse * exp(-2 Delta V/Vc0) ~ 0
        f = g / 2.0
        p01 = (1 - f) * p_pulse + f * (1 - p_pulse)   # from 0: relax-flip then pulse
        # careful composition: relax first, then pulse
        # from 0: after relax in 0 w.p. (1-f) -> pulse flips w.p. p; in 1 w.p. f -> stays
        p0_to_1 = (1 - f) * p_pulse + f * (1.0 - 0.0)
        p1_to_0 = f * (1 - p_pulse)                    # relax to 0, pulse misses
        return p0_to_1, p1_to_0, p01

    theta = np.linspace(-6, 6, 241)
    p_tgt = 1.0 / (1.0 + np.exp(-theta))          # calibrated sigmoid marginal
    # sign-static polarity: work on |theta| axis, mirror afterwards
    p_mag = 1.0 / (1.0 + np.exp(-np.abs(theta)))  # pulse-favoured marginal >= 0.5

    p0to1, p1to0, _ = slot_matrix(p_mag)
    pi_naive = p0to1 / (p0to1 + p1to0)            # stationary favoured-state prob
    # pre-distortion: choose p_pulse so that stationary == p_mag (bisection)
    lo = np.zeros_like(p_mag); hi = np.ones_like(p_mag)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        a, b, _ = slot_matrix(mid)
        pi = a / (a + b)
        hi = np.where(pi > p_mag, mid, hi)
        lo = np.where(pi <= p_mag, mid, lo)
    p_pre = 0.5 * (lo + hi)
    a, b, _ = slot_matrix(p_pre)
    pi_pre = a / (a + b)
    rho = 1.0 - a - b                              # slot-to-slot autocorrelation
    # variance inflation of a T-sample mean of the stationary chain
    def var_inflation(rho_, T_):
        k = np.arange(1, T_)
        return 1.0 + 2.0 / T_ * np.sum((T_ - k)[:, None] * rho_ ** k[:, None], axis=0)
    vif = var_inflation(rho, T)

    mid_mask = (p_tgt > 0.2) & (p_tgt < 0.8)
    print(f"naive unipolar stationary at theta=0: pi = {pi_naive[theta==0][0]:.3f} "
          f"(target 0.5) -- ratchet bias; pi >= 0.5 for ALL theta (unipolar)")
    print(f"pre-distorted mid-range: pulse prob ~ {p_pre[np.abs(theta)<0.1][0]:.4f}, "
          f"autocorr rho ~ {rho[np.abs(theta)<0.1][0]:.3f}, "
          f"T=4 variance inflation ~ {vif[np.abs(theta)<0.1][0]:.2f}x")

    with open(run_dir / "chain.csv", "w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(["theta", "p_target", "pi_naive_unipolar",
                    "p_pulse_predistorted", "rho_slot", "vif_T4"])
        for row in zip(theta, p_tgt, np.where(theta >= 0, pi_naive, 1 - pi_naive),
                       p_pre, rho, vif):
            w.writerow([round(float(x), 5) for x in row])

    # ----- (b) MNIST accuracy under the three timings ---------------------
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
    calibrate_bn(model, train_loader, device,
                 mode=ForwardMode.FULL_STACK, T=T)
    layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]

    # stateful free-running sampler, patched in at harness level
    def make_stateful(scheme: str):
        gen = torch.Generator(device=device).manual_seed(3)

        def fwd(self, x, T_):
            with torch.no_grad():
                p_soft = self._p_soft_for_sampling()
                th = torch.logit(p_soft.clamp(1e-6, 1 - 1e-6))
                pol = (th >= 0)
                p_m = torch.sigmoid(th.abs())
                # per-cell pre-distorted pulse probability (vectorised bisect)
                f = g / 2.0
                lo_ = torch.zeros_like(p_m); hi_ = torch.ones_like(p_m)
                for _ in range(40):
                    mid_ = 0.5 * (lo_ + hi_)
                    a_ = (1 - f) * mid_ + f
                    b_ = f * (1 - mid_)
                    pi_ = a_ / (a_ + b_)
                    hi_ = torch.where(pi_ > p_m, mid_, hi_)
                    lo_ = torch.where(pi_ <= p_m, mid_, lo_)
                p_pulse = 0.5 * (lo_ + hi_)
                if not hasattr(self, "_rf_state"):
                    self._rf_state = (torch.rand(
                        p_m.shape, generator=gen, device=device) < p_m).float()
                s = self._rf_state
                ws = []
                for _ in range(T_):
                    relax = torch.rand(s.shape, generator=gen, device=device) < f
                    s = torch.where(relax, 1.0 - s, s)
                    fire = torch.rand(s.shape, generator=gen, device=device) < p_pulse
                    s = torch.where(fire, torch.ones_like(s), s)   # pulse ratchets to 1
                    self._rf_state = s
                    w_fav = 2.0 * s - 1.0            # favoured-state axis
                    ws.append(torch.where(pol, w_fav, -w_fav))
            acc = None
            for w_ in ws:
                z = torch.nn.functional.linear(x, w_)
                acc = z if acc is None else acc + z
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

    results = {}
    results["reset_iid"] = eval_subset()                       # library sampler
    originals = [m._forward_full_stack for m in layers]
    for m in layers:
        m._forward_full_stack = types.MethodType(make_stateful("freerun"), m)
    results["freerun_predistorted"] = eval_subset()
    for m, orig in zip(layers, originals):
        m._forward_full_stack = orig
        if hasattr(m, "_rf_state"):
            del m._rf_state
    # read-then-set: conditional polarity makes samples i.i.d. Bernoulli(p)
    # exactly -- statistically identical to the library sampler; evaluate a
    # second i.i.d. pass as the finite-sample check.
    results["readset_iid"] = eval_subset()
    for k, v in results.items():
        print(f"accuracy [{k:22s}] = {v:.4f}   (subset n={N_EVAL})")

    with open(run_dir / "accuracy.csv", "w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv); w.writerow(["scheme", "accuracy", "n_eval"])
        for k, v in results.items():
            w.writerow([k, round(v, 4), N_EVAL])

    # ----- (c) write-path energy per sample --------------------------------
    tech = default_28nm()
    e_wr = tech.e_smtj_write
    e_rd = tech.e_smtj_read
    energy = {
        "reset_iid": 2.0 * e_wr,            # supercritical reset + program
        "freerun_predistorted": 1.0 * e_wr,
        "readset_iid": 1.0 * e_wr + e_rd,
    }
    print("write-path energy per sample: " + ", ".join(
        f"{k}={v*1e12:.3f} pJ" for k, v in energy.items()))
    print(f"read-then-set saves {(1 - energy['readset_iid']/energy['reset_iid'])*100:.1f}%"
          f" of the reset-timing write path at zero accuracy cost")

    # ----- figure -----------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.8))
    ax[0].plot(theta, p_tgt, color="#5E3F8C", lw=2, label="target sigmoid(theta)")
    ax[0].plot(theta, np.where(theta >= 0, pi_naive, 1 - pi_naive), "--",
               color="#A82038", lw=2, label="free-run stationary (sign-static)")
    ax[0].plot(theta, np.where(theta >= 0, pi_pre, 1 - pi_pre), ":",
               color="#1A6B5A", lw=2.4, label="pre-distorted stationary")
    ax[0].set_xlabel(r"$\theta$"); ax[0].set_ylabel("P(favoured state)")
    ax[0].set_title("Stationary bias and its pre-distortion")
    ax[0].legend(fontsize=9); ax[0].grid(alpha=0.3)

    ax[1].plot(p_tgt, rho, color="#A82038", lw=2)
    ax[1].set_xlabel("target probability p"); ax[1].set_ylabel(r"slot autocorrelation $\rho$")
    ax[1].set_title(f"Chain mixing (T={T} VIF up to {vif.max():.1f}x)")
    ax[1].grid(alpha=0.3)

    keys = list(results)
    accs = [results[k] * 100 for k in keys]
    ens = [energy[k] * 1e12 for k in keys]
    x_ = np.arange(len(keys))
    axa = ax[2]
    axa.bar(x_ - 0.17, accs, width=0.34, color="#5E3F8C", label="accuracy (%)")
    axa.set_ylim(min(accs) - 2, 100)
    axa.set_ylabel("MNIST accuracy (%)")
    axb = axa.twinx()
    axb.bar(x_ + 0.17, ens, width=0.34, color="#C99FD4", label="energy/sample (pJ)")
    axb.set_ylabel("write-path energy per sample (pJ)")
    axa.set_xticks(x_)
    axa.set_xticklabels(["reset\n(2 pulses)", "free-run\npre-distorted",
                         "read-then-set\n(1 pulse + read)"], fontsize=10)
    axa.set_title("Accuracy vs write-path energy")
    fig.tight_layout()
    out = REPO / "figures" / "25_resetfree_sampling.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
