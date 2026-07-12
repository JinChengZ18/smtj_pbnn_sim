"""30 -- Full-temperature self-consistency of the calibrated interface (T2-2).

Chapter 2 calibrates the Sigmoid interface at a single 300 K anchor; the RC
chapter's temperature study scaled only the kT denominator of Delta. This
experiment propagates the platform's own magnetic scaling laws (Bloch M_s,
Callen-Callen K_i) through the near-compensated effective anisotropy to
every network-facing quantity, and asks the system question: over what
ambient window does the deployed network survive, and what does the trim
DAC have to do about it?

Temperature drift is a COMMON-MODE shift -- every cell moves together --
which is a different failure axis from the random D2D mismatch already
studied. With the checkpoint's nominal calibration (p = sigmoid(theta) in
V_T_nom = 0.022422 V units, variation off), operating a 300 K-programmed
cell at T gives EXACTLY

    p_T = sigmoid(a(T) theta + b(T)),  a(T) = 300/T (universal),
    b(T) = -dV_th(T) * 300 / (V_T_nom_model * T),

applied directly on theta (no logit reconstruction, so strongly
programmed cells with |theta| up to ~58 are handled exactly). The V_th
shift dV_th(T) -- and only it -- depends on the compensation REALIZATION
of the superparamagnetic variant and on the Callen-Callen exponent n;
scenarios per temperature:

  no_recal (x3)  -- full Neel-Brown chain for the as-built (c = 0.811),
                    trim-route (c = 0.977, pessimistic) and shrink-route
                    (c = 0.726, mildest) realizations, nothing
                    recalibrated (thermal-activation picture);
  slope_only     -- b = 0, a(T) = 300/T kept. Realization- and
                    n-independent (vt_of_T = V_T (T/300) identically).
                    Doubles as (i) any pessimistic chain after one
                    common-mode trim refresh and (ii) the optimistic
                    ballistic end (threshold athermal at sub-ns pulses,
                    Rehm et al., arXiv:2310.18779).

The n in [1.8, 2.8] literature band enters b(T) only; its windows are
obtained by inverting |b(T)| = b_crit (the measured b at the as-built
1pp edges) for each (realization, n) -- the inversion is validated
against the directly measured trim/shrink windows in the same run.

BN statistics stay frozen at the 300 K calibration, calibrated at the
same read count as the evaluation (T = 8). C2C noise is ABSENT in this
checkpoint (sigma_c2c = 0), not merely athermal. Single-seed read noise
is shared across all points (paired comparison); the per-point binomial
SE (~0.35 pp at n = 4000) maps to roughly +-1 K of window-edge
uncertainty. Positioning note for the manuscript: arXiv:2410.16915
compensates temperature in weight space; here the window/trim spec is
derived device-side from the platform's own scaling laws.

Outputs: runs/30_temperature_selfconsistency_<ts>/{summary.json,
accuracy.csv, chain.csv} + figures/30_temperature_selfconsistency.png

Run from the repo root:  python experiments/30_temperature_selfconsistency.py
"""

from __future__ import annotations

import csv
import json
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

TEMPS_ACC = (250.0, 260.0, 270.0, 280.0, 285.0, 290.0, 295.0, 300.0,
             305.0, 310.0, 315.0, 320.0, 330.0, 340.0, 360.0, 380.0, 400.0)
N_EVAL = 4000
T_READS = 8
TRIM_LSB_MV = (1.6, 3.1)      # C2 trim-DAC LSB range [mV]
ACC_DROPS = (0.01, 0.05)
N_BAND = (1.8, 2.18, 2.8)


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import torch

    from smtj_pbnn_sim.device import thermal_scaling as ts
    from smtj_pbnn_sim.device.telegraph import relaxation_time
    from smtj_pbnn_sim.nn.pbnn_linear import ForwardMode, PBNNLinear
    from smtj_pbnn_sim.data.mnist import get_mnist_loaders
    from smtj_pbnn_sim.train.train_loop import calibrate_bn
    from smtj_pbnn_sim.scripts._mnist_eval import _device_params_from_cfg
    from smtj_pbnn_sim.scripts._mnist_train import PBNN_MLP
    from smtj_pbnn_sim.utils.seeding import set_global_seed
    from smtj_pbnn_sim.utils.io import make_run_dir

    plt.rcParams.update({"font.family": "Arial", "font.size": 13,
                         "axes.labelsize": 14, "axes.titlesize": 14})
    set_global_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    run_dir = make_run_dir("30_temperature_selfconsistency", base=REPO / "runs")

    stacks = {"as_built": ts.ThermalStack(),
              "trim": ts.trim_route(),
              "shrink": ts.shrink_route()}

    # ---- analytic chain (as-built realization) ----------------------------
    stack = stacks["as_built"]
    T_dense = np.linspace(250.0, 420.0, 171)
    chain = dict(
        T=T_dense,
        keff=ts.keff_ratio(T_dense, stack),
        delta=ts.delta_of_T(T_dense, stack),
        dvth_mV=ts.vth_shift(T_dense, stack) * 1e3,
        dvth_trim_mV=ts.vth_shift(T_dense, stacks["trim"]) * 1e3,
        dvth_shrink_mV=ts.vth_shift(T_dense, stacks["shrink"]) * 1e3,
        vt_mV=ts.vt_of_T(T_dense, stack) * 1e3,
        tmr=ts.tmr_of_T(T_dense, stack),
    )
    tau_corr = np.array([float(relaxation_time(0.0, Delta=d))
                         for d in chain["delta"]])
    tau_simp = np.array([float(relaxation_time(0.0, Delta=stack.Delta * 300.0 / T))
                         for T in T_dense])
    chain["tau_corr_ns"] = tau_corr * 1e9
    chain["tau_simp_ns"] = tau_simp * 1e9

    with open(run_dir / "chain.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.writer(fc)
        w.writerow(list(chain.keys()))
        w.writerows(np.column_stack(list(chain.values())))

    # ---- model + exact common-mode patch ----------------------------------
    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=250, num_workers=0)
    state = torch.load(REPO / "runs" / "mnist_pbnn_mlp" / "best.pt",
                       map_location="cpu")
    cfg = state["config"]
    dp = _device_params_from_cfg(cfg.get("device", {}))
    vt_model = float(dp.V_T_nom)          # 0.022422 V: the simulated family
    model = PBNN_MLP(hidden=int(cfg.get("model", {}).get("hidden", 1024)),
                     device_params=dp, variation_cfg=None,
                     T_full_stack=1).to(device)
    model.load_state_dict(state["model_state"], strict=True)
    calibrate_bn(model, train_loader, device, mode=ForwardMode.FULL_STACK,
                 T=T_READS)
    layers = [m for m in model.modules() if isinstance(m, PBNNLinear)]

    def patch_common(a: float, b: float):
        """Exact common-mode transform: p = sigmoid(a theta + b).

        With variation off the layer's own p is sigmoid(theta), so this
        is exact for every |theta| (no logit-reconstruction clamp).
        """
        for m in layers:
            def p_soft(self, _a=a, _b=b):
                return torch.sigmoid(_a * self.theta + _b)
            m._p_soft_for_sampling = types.MethodType(p_soft, m)

    def unpatch():
        for m in layers:
            if "_p_soft_for_sampling" in m.__dict__:
                del m._p_soft_for_sampling

    @torch.no_grad()
    def eval_acc() -> float:
        correct, n = 0, 0
        for x, y in test_loader:
            x = x.to(device)
            logits = model.forward_with_mode(
                x, mode=ForwardMode.FULL_STACK, T=T_READS)
            correct += int((logits.argmax(1).cpu() == y).sum())
            n += int(y.numel())
            if n >= N_EVAL:
                break
        return correct / n

    def b_of(T: float, st) -> float:
        return -float(ts.vth_shift(T, st)) * 300.0 / (vt_model * T)

    # ---- accuracy sweep ----------------------------------------------------
    scenarios = [("no_recal_as_built", stacks["as_built"]),
                 ("no_recal_trim", stacks["trim"]),
                 ("no_recal_shrink", stacks["shrink"]),
                 ("slope_only", None)]
    rows = []
    for T in TEMPS_ACC:
        a = 300.0 / T
        for scen, st in scenarios:
            b = 0.0 if st is None else b_of(T, st)
            set_global_seed(1234)          # same read noise across points
            patch_common(a, b)
            acc = eval_acc()
            unpatch()
            rows.append(dict(T_K=T, scenario=scen, a=a, b=b, acc=acc))
            print(f"T={T:5.1f} K {scen:18s}: a={a:.4f} b={b:+8.3f} "
                  f"acc={acc:.4f}", flush=True)

    with open(run_dir / "accuracy.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.DictWriter(fc, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- window extraction -------------------------------------------------
    acc_ref = float(np.mean([r["acc"] for r in rows if r["T_K"] == 300.0]))

    def crossings(scen: str, drop: float):
        pts = sorted([(r["T_K"], r["acc"]) for r in rows
                      if r["scenario"] == scen])
        Ts = np.array([p[0] for p in pts])
        accs = np.array([p[1] for p in pts])
        thr = acc_ref - drop
        below = accs < thr
        i300 = int(np.argmin(np.abs(Ts - 300.0)))
        lo = hi = float("nan")
        for i in range(i300, 0, -1):
            if below[i - 1] and not below[i]:
                lo = float(np.interp(thr, [accs[i - 1], accs[i]],
                                     [Ts[i - 1], Ts[i]]))
                break
        for i in range(i300, len(Ts) - 1):
            if below[i + 1] and not below[i]:
                hi = float(np.interp(thr, [accs[i + 1], accs[i]],
                                     [Ts[i + 1], Ts[i]]))
                break
        return lo, hi

    windows = {}
    for scen, _ in scenarios:
        for drop in ACC_DROPS:
            lo, hi = crossings(scen, drop)
            windows[f"{scen}_{int(drop * 100)}pp"] = [lo, hi]
            print(f"window {scen} -{int(drop * 100)}pp: "
                  f"[{lo:.1f}, {hi:.1f}] K (edge uncertainty ~ +-1 K)",
                  flush=True)

    # ---- n-band window table via b_crit inversion --------------------------
    lo_ab, hi_ab = windows["no_recal_as_built_1pp"]
    b_crit_cold = b_of(lo_ab, stacks["as_built"])
    b_crit_hot = b_of(hi_ab, stacks["as_built"])
    Td = np.linspace(220.0, 460.0, 2401)

    def invert_window(st) -> list:
        """Contiguous interval around 300 K where b_cold <= b(T) <= b_hot.

        Robust to slope-sign reversal (e.g. trim realization at n = 1.8,
        where K_eff(T) increases with T and the window flips sides).
        """
        bT = np.array([b_of(float(t), st) for t in Td])
        ok = (bT >= min(b_crit_cold, b_crit_hot)) &              (bT <= max(b_crit_cold, b_crit_hot))
        i300 = int(np.argmin(np.abs(Td - 300.0)))
        if not ok[i300]:
            return [float("nan"), float("nan")]
        lo = i300
        while lo > 0 and ok[lo - 1]:
            lo -= 1
        hi = i300
        while hi < len(Td) - 1 and ok[hi + 1]:
            hi += 1
        return [float(Td[lo]), float(Td[hi])]

    from dataclasses import replace
    nband_windows = {}
    for real, st0 in stacks.items():
        for n in N_BAND:
            st = replace(st0, cc_exponent=n)
            nband_windows[f"{real}_n{n}"] = invert_window(st)
    # inversion validation: predicted-vs-measured for trim/shrink at n=2.18
    inv_check = {
        real: dict(predicted=nband_windows[f"{real}_n2.18"],
                   measured=windows[f"no_recal_{real}_1pp"])
        for real in ("trim", "shrink")
    }

    dvth_per_K = {real: float((ts.vth_shift(310.0, st)
                               - ts.vth_shift(290.0, st)) / 20.0) * 1e3
                  for real, st in stacks.items()}
    tau_ratio_350 = float(np.interp(350.0, T_dense, tau_corr / tau_simp))
    tau_ratio_400 = float(np.interp(400.0, T_dense, tau_corr / tau_simp))
    summary = dict(
        acc_ref_300K=acc_ref, vt_model_V=vt_model,
        windows_K=windows, window_edge_uncertainty_K=1.0,
        note_trim_measured="trim no-recal window is limited by the 5 K accuracy grid near 300 K; quote the continuous b_crit inversion instead",
        nband_windows_1pp_K=nband_windows,
        inversion_validation=inv_check,
        dvth_per_K_mV=dvth_per_K,
        b_crit_1pp=dict(cold=b_crit_cold, hot=b_crit_hot),
        trim_lsb_mV=list(TRIM_LSB_MV),
        rc_clock_rescale_vs_simplified={"350K": tau_ratio_350,
                                        "400K": tau_ratio_400},
        caliber="single 300 K anchor + platform scaling laws; frozen BN "
                "calibrated at T=8 reads; C2C ABSENT in this checkpoint "
                "(sigma_c2c=0); realization band {as_built 0.811, trim "
                "0.977, shrink 0.726} and Callen-Callen n in [1.8, 2.8] "
                "enter b(T) only; slope_only is realization/n-independent "
                "and doubles as trim-refreshed pessimistic AND athermal-"
                "threshold optimistic (Rehm arXiv:2310.18779); windows "
                "quoted +-1 K; weight-space compensation route for "
                "contrast: arXiv:2410.16915",
    )
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1),
                                          encoding="utf-8")

    # ---- figure ------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.6))

    ax = axes[0]
    ax.plot(T_dense, chain["keff"], color="tab:blue", lw=2,
            label="K_eff ratio")
    ax.plot(T_dense, chain["delta"] / stack.Delta, color="tab:orange", lw=2,
            label=r"$\Delta/\Delta_{300}$")
    ax.plot(T_dense, chain["vt_mV"] / (stack.V_T * 1e3), color="tab:green",
            lw=2, label=r"$V_T/V_{T,300}$")
    ax.plot(T_dense, chain["tmr"], color="tab:purple", lw=2, ls="--",
            label="TMR ratio")
    ax.axhline(1.0, color="0.6", lw=0.8)
    ax.axvline(300.0, color="0.6", lw=0.8, ls=":")
    ax2 = ax.twinx()
    ax2.plot(T_dense, chain["dvth_mV"], color="tab:red", lw=2.5)
    ax2.plot(T_dense, chain["dvth_trim_mV"], color="tab:red", lw=1.2,
             ls="--")
    ax2.plot(T_dense, chain["dvth_shrink_mV"], color="tab:red", lw=1.2,
             ls=":")
    ax2.set_ylabel(r"$V_{th}$ shift (mV): as-built / trim / shrink",
                   color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")
    ax.set_xlabel("ambient temperature (K)")
    ax.set_ylabel("ratio to 300 K anchor")
    ax.set_title("scaling chain through the compensated K_eff")
    ax.legend(fontsize=10, loc="lower left")

    ax = axes[1]
    for scen, color, ls, label in (
            ("no_recal_as_built", "tab:red", "-", "no recal, as-built c=0.81"),
            ("no_recal_trim", "tab:red", "--", "no recal, trim c=0.98"),
            ("no_recal_shrink", "tab:red", ":", "no recal, shrink c=0.73"),
            ("slope_only", "tab:blue", "-",
             "trim-refreshed / athermal threshold")):
        pts = sorted([(r["T_K"], r["acc"]) for r in rows
                      if r["scenario"] == scen])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-" if ls == "-"
                else ls, color=color, lw=2, ms=4, label=label)
    for drop, lsd in zip(ACC_DROPS, ("--", ":")):
        ax.axhline(acc_ref - drop, color="0.4", lw=1, ls=lsd)
        ax.text(402, acc_ref - drop, f"-{int(drop * 100)}pp", fontsize=10,
                va="bottom", color="0.3")
    if np.isfinite(lo_ab) and np.isfinite(hi_ab):
        ax.axvspan(lo_ab, hi_ab, color="tab:red", alpha=0.08)
    ax.axvline(300.0, color="0.6", lw=0.8, ls=":")
    ax.set_xlabel("ambient temperature (K)")
    ax.set_ylabel(f"MNIST accuracy (T={T_READS} reads)")
    ax.set_ylim(0.05, 1.0)
    ax.set_title("common-mode drift: deployed-network window")
    ax.legend(fontsize=9, loc="lower center")

    ax = axes[2]
    ax.semilogy(T_dense, chain["tau_corr_ns"], color="tab:blue", lw=2,
                label=r"$\tau(T)$, barrier + kT (this work)")
    ax.semilogy(T_dense, chain["tau_simp_ns"], color="tab:orange", lw=2,
                ls="--", label=r"$\tau(T)$, kT only (simplified)")
    ax.axvline(300.0, color="0.6", lw=0.8, ls=":")
    ax.set_xlabel("ambient temperature (K)")
    ax.set_ylabel(r"$\tau$(0 V) (ns)")
    ax.set_title("RC thermal clock: corrected temperature axis")
    ax.legend(fontsize=10, loc="upper right")
    ax3 = ax.twinx()
    ax3.plot(T_dense, tau_corr / tau_simp, color="tab:green", lw=1.5)
    ax3.set_ylabel("corrected / simplified", color="tab:green")
    ax3.tick_params(axis="y", labelcolor="tab:green")

    fig.tight_layout()
    fig_path = REPO / "figures" / "30_temperature_selfconsistency.png"
    fig.savefig(fig_path, dpi=200, bbox_inches="tight")
    print(f"figure saved: {fig_path}")
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
