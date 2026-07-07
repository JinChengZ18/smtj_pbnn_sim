"""24 -- V_th slow-drift stress test and recalibration cadence.

The nonideality ablation (experiment 08) established that the absolute
position of V_th is the accuracy-critical device parameter, but only as a
STATIC dispersion. This experiment adds the time axis: slowly accumulating
per-cell (device aging) and per-column (shared write-DAC/driver drift)
V_th offsets, injected at the harness level into the calibrated PBNN
checkpoint's ``V_th_field`` buffers -- the device core and the RNG
discipline stay untouched.

Parts
-----
  (a) static tolerance: accuracy vs instantaneous offset dispersion
      sigma/V_T, separately for per-cell and per-column offsets. The
      -0.5 pp crossing defines the drift budget x* for each mode.
  (b) dynamic validation: an unbounded random walk in the per-column
      mode (the binding one), sigma_step chosen to cross x* around
      block ~30, under three policies: no recalibration, BN
      recalibration every 15 blocks, write-DAC trim refresh every 15
      blocks (zeroes the accumulated drift, emulating the 3-4 bit
      per-column trim). A per-cell walk at the same step size is run
      as contrast.

The cadence formula follows from the random-walk scaling: after N
blocks the accumulated dispersion is sigma_step * sqrt(N), so the
refresh interval that keeps accuracy within the budget is
N* = (x* / sigma_step)^2; for an OU (bounded) drift with correlation
time tau_c the stationary dispersion sigma_inf = sigma_step *
sqrt(tau_c / 2) either stays below x* (no refresh needed) or the same
N* applies to the initial transit. The time axis is operation-block
count -- mapping blocks to wall-clock is device-specific and is left
parametric (no lifetime claims).

Outputs:
  runs/24_vth_drift_<ts>/{tolerance.csv, drift_traces.csv}
  figures/24_vth_drift.png

Run from the repo root:

    python experiments/24_vth_drift.py
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

ACC_BUDGET_PP = 0.5          # tolerated accuracy drop that defines x*
SIGMAS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]   # in units of V_T
N_BLOCKS = 60
REFRESH_EVERY = 15
EVAL_EVERY = 3


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir
    from smtj_pbnn_sim.ppa.tech_params import default_28nm

    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("24_vth_drift", base=REPO / "runs")
    T = 4

    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=256, num_workers=0)

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

    # one forward draws the (uniform) variation fields; then they are ours
    x0, _ = next(iter(test_loader))
    with torch.no_grad():
        model.forward_with_mode(x0.to(device), mode=ForwardMode.FULL_STACK, T=T)
    layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]
    base_fields = [m.V_th_field.clone() for m in layers]
    V_T = dp.V_T_nom

    def set_offsets(offsets) -> None:
        with torch.no_grad():
            for m, base, off in zip(layers, base_fields, offsets):
                m.V_th_field = base + off

    def evaluate() -> float:
        return exp07._eval_with_noise(model, test_loader, device, None,
                                      mode=ForwardMode.FULL_STACK, T=T)

    def draw(mode: str, scale: float, gen: torch.Generator):
        outs = []
        for base in base_fields:
            if mode == "per_cell":
                o = torch.randn(base.shape, generator=gen,
                                device=base.device) * scale
            else:  # per_column: one offset per output row, shared across inputs
                o = torch.randn((base.shape[0], 1), generator=gen,
                                device=base.device) * scale
                o = o.expand_as(base).contiguous()
            outs.append(o)
        return outs

    baseline = evaluate()
    print(f"baseline (FULL_STACK T={T}): {baseline:.4f}")

    # ----- (a) static tolerance ------------------------------------------
    gen = torch.Generator(device=device).manual_seed(7)
    tol_rows = []
    tol = {"per_cell": [], "per_column": []}
    for mode in ("per_cell", "per_column"):
        for s in SIGMAS:
            if s == 0.0:
                acc = baseline
            else:
                accs = []
                for _ in range(2):        # two field draws to tame draw noise
                    set_offsets(draw(mode, s * V_T, gen))
                    accs.append(evaluate())
                acc = float(np.mean(accs))
            tol[mode].append(acc)
            tol_rows.append({"mode": mode, "sigma_over_VT": s,
                             "accuracy": round(acc, 4)})
            print(f"  static {mode:10s} sigma={s:4.2f} V_T  acc={acc:.4f}")
    set_offsets([torch.zeros_like(b) for b in base_fields])

    def crossing(sig, accs) -> float:
        thr = baseline - ACC_BUDGET_PP / 100.0
        for i in range(1, len(sig)):
            if accs[i] < thr <= accs[i - 1]:
                f = (accs[i - 1] - thr) / (accs[i - 1] - accs[i])
                return sig[i - 1] + f * (sig[i] - sig[i - 1])
        return float("nan")

    x_cell = crossing(SIGMAS, tol["per_cell"])
    x_col = crossing(SIGMAS, tol["per_column"])
    print(f"drift budget x* (-{ACC_BUDGET_PP} pp): per_cell={x_cell:.2f} V_T, "
          f"per_column={x_col:.2f} V_T")

    # ----- (b) random-walk validation (binding mode: per_column) ----------
    sigma_step = (x_col if np.isfinite(x_col) else 1.0) / np.sqrt(30.0)
    n_star = (x_col / sigma_step) ** 2 if np.isfinite(x_col) else float("nan")
    print(f"random walk: sigma_step={sigma_step:.3f} V_T/block "
          f"-> predicted N* = {n_star:.0f} blocks; refresh every "
          f"{REFRESH_EVERY} blocks in the policy runs")

    traces: dict[str, list] = {}
    plans = [("per_column", "none"), ("per_column", "bn"),
             ("per_column", "trim"), ("per_cell", "none")]
    for mode, policy in plans:
        gen_w = torch.Generator(device=device).manual_seed(11)
        drift = [torch.zeros_like(b) for b in base_fields]
        pts = [(0, baseline)]
        for blk in range(1, N_BLOCKS + 1):
            step = draw(mode, sigma_step * V_T, gen_w)
            drift = [d + s for d, s in zip(drift, step)]
            if policy == "trim" and blk % REFRESH_EVERY == 0:
                drift = [torch.zeros_like(d) for d in drift]   # DAC re-trim
            set_offsets(drift)
            if policy == "bn" and blk % REFRESH_EVERY == 0:
                calibrate_bn(model, train_loader, device,
                             mode=ForwardMode.FULL_STACK, T=T)
            if blk % EVAL_EVERY == 0:
                pts.append((blk, evaluate()))
        traces[f"{mode}/{policy}"] = pts
        print(f"  walk {mode}/{policy}: " +
              " ".join(f"{b}:{a:.3f}" for b, a in pts[::4]))
        set_offsets([torch.zeros_like(b) for b in base_fields])
        if policy == "bn":       # restore clean BN stats for the next plan
            calibrate_bn(model, train_loader, device,
                         mode=ForwardMode.FULL_STACK, T=T)

    # ----- recalibration cost (order of magnitude) -------------------------
    tech = default_28nm()
    n_cols = sum(b.shape[0] for b in base_fields)
    e_trim = n_cols * tech.e_dac_step
    print(f"trim refresh energy ~ {n_cols} columns x e_dac_step = "
          f"{e_trim*1e12:.2f} pJ per refresh event (negligible vs the "
          f"~uJ-scale inference between refreshes)")

    # ----- persist ----------------------------------------------------------
    with open(run_dir / "tolerance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["mode", "sigma_over_VT", "accuracy"])
        w.writeheader(); w.writerows(tol_rows)
    with open(run_dir / "drift_traces.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["mode_policy", "block", "accuracy"])
        for key, pts in traces.items():
            for b, a in pts:
                w.writerow([key, b, round(a, 4)])
    print(f"CSVs written to {run_dir}")

    # ----- figure -----------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.2))
    ax[0].plot(SIGMAS, [a * 100 for a in tol["per_cell"]], "o-",
               color="#5E3F8C", lw=2, label="per-cell offsets")
    ax[0].plot(SIGMAS, [a * 100 for a in tol["per_column"]], "s-",
               color="#A82038", lw=2, label="per-column offsets")
    ax[0].axhline((baseline - ACC_BUDGET_PP / 100) * 100, color="grey",
                  ls=":", lw=1.2)
    ax[0].set_xlabel(r"offset dispersion $\sigma / V_T$")
    ax[0].set_ylabel("MNIST test accuracy (%)")
    ax[0].set_title("Static drift tolerance")
    ax[0].legend(fontsize=10); ax[0].grid(alpha=0.3)

    styles = {"per_column/none": ("#A82038", "-", "column walk, no refresh"),
              "per_column/bn": ("#1A6B5A", "--", "BN recalibration"),
              "per_column/trim": ("#5E3F8C", "-.", "DAC trim refresh"),
              "per_cell/none": ("#C99FD4", ":", "cell walk, no refresh")}
    for key, (c, ls, lab) in styles.items():
        b, a = zip(*traces[key])
        ax[1].plot(b, [x * 100 for x in a], ls, color=c, lw=2, label=lab)
    for r in range(REFRESH_EVERY, N_BLOCKS + 1, REFRESH_EVERY):
        ax[1].axvline(r, color="grey", alpha=0.25, lw=0.8)
    ax[1].set_xlabel(r"operation blocks (random walk, "
                     r"$\sigma_\mathrm{step}$ per block)")
    ax[1].set_ylabel("MNIST test accuracy (%)")
    ax[1].set_title("Drift walk and recalibration cadence")
    ax[1].legend(fontsize=10); ax[1].grid(alpha=0.3)
    fig.tight_layout()
    out = REPO / "figures" / "24_vth_drift.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
