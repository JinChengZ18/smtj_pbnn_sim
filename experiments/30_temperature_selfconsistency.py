"""30 -- Full-temperature self-consistency of the calibrated interface (T2-2).

Chapter 2 calibrates the Sigmoid interface at a single 300 K anchor; the RC
chapter's temperature study scaled only the kT denominator of Delta. This
experiment propagates the platform's own magnetic scaling laws (Bloch M_s,
Callen-Callen K_i, exponent 2.18) through the 81%-compensated effective
anisotropy to every network-facing quantity, and asks the system question:
over what ambient window does the deployed network survive, and what does
the trim DAC have to do about it?

Temperature drift is a COMMON-MODE shift -- every cell moves together --
which is a different failure axis from the random D2D mismatch already
studied: the per-cell logit transform is p -> sigmoid(a(T) logit(p) + b(T))
with the SAME scalars a(T) = V_T/V_T(T), b(T) = -dV_th(T)/V_T(T) for all
cells. Two deployment scenarios per temperature:

  no_recal    -- full Neel-Brown chain, nothing recalibrated (pessimistic
                 thermal-activation end);
  slope_only  -- b = 0, a(T) kept. This single curve serves double duty:
                 it is BOTH the pessimistic chain after one common-mode
                 trim refresh (offset cancelled, window mismatch left)
                 AND the optimistic ballistic-end scenario in which the
                 switching threshold is athermal and only the statistics
                 move. The operating pulse (0.75 ns) sits in the
                 activation/ballistic crossover, so the two curves bracket
                 the deployable window.

BN statistics stay frozen at the 300 K calibration (deployment caliber,
same as the bit-flip certification). C2C sigma is treated as athermal.

The same corrected Delta(T) also fixes the RC thermal-clock axis: exp19
used Delta * 300/T (denominator only); with the barrier E_b(T) also
falling, tau(0 V) shrinks much faster, changing the clock-rescale recipe.

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
    stack = ts.ThermalStack()

    # ---- analytic chain ---------------------------------------------------
    T_dense = np.linspace(250.0, 420.0, 171)
    chain = dict(
        T=T_dense,
        keff=ts.keff_ratio(T_dense, stack),
        delta=ts.delta_of_T(T_dense, stack),
        dvth_mV=ts.vth_shift(T_dense, stack) * 1e3,
        vt_mV=ts.vt_of_T(T_dense, stack) * 1e3,
        tmr=ts.tmr_of_T(T_dense, stack),
    )
    tau_corr = np.array([float(relaxation_time(0.0, Delta=d))
                         for d in chain["delta"]])
    tau_simp = np.array([float(relaxation_time(0.0, Delta=stack.Delta * 300.0 / T))
                         for T in T_dense])
    tau_300 = float(np.interp(300.0, T_dense, tau_corr))
    chain["tau_corr_ns"] = tau_corr * 1e9
    chain["tau_simp_ns"] = tau_simp * 1e9

    with open(run_dir / "chain.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.writer(fc)
        w.writerow(list(chain.keys()))
        w.writerows(np.column_stack(list(chain.values())))

    # ---- model + patch machinery -----------------------------------------
    train_loader, test_loader = get_mnist_loaders(
        root="./data/mnist", batch_size=250, num_workers=0)
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

    def patch_common(a: float, b: float):
        """Common-mode logit transform, identical scalars on every cell."""
        for m in layers:
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

    # ---- accuracy sweep ---------------------------------------------------
    rows = []
    for T in TEMPS_ACC:
        vt_T = float(ts.vt_of_T(T, stack))
        a = stack.V_T / vt_T
        b_full = -float(ts.vth_shift(T, stack)) / vt_T
        for scen, b in (("no_recal", b_full), ("slope_only", 0.0)):
            set_global_seed(1234)          # same read noise across points
            patch_common(a, b)
            acc = eval_acc()
            unpatch()
            rows.append(dict(T_K=T, scenario=scen, a=a, b=b, acc=acc))
            print(f"T={T:5.1f} K {scen:10s}: a={a:.4f} b={b:+7.3f} "
                  f"acc={acc:.4f}", flush=True)

    with open(run_dir / "accuracy.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.DictWriter(fc, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- window extraction ------------------------------------------------
    acc_ref = float(np.mean([r["acc"] for r in rows
                             if r["T_K"] == 300.0]))

    def crossings(scen: str, drop: float):
        pts = sorted([(r["T_K"], r["acc"]) for r in rows
                      if r["scenario"] == scen])
        Ts = np.array([p[0] for p in pts])
        accs = np.array([p[1] for p in pts])
        thr = acc_ref - drop
        lo, hi = Ts[0], Ts[-1]
        below = accs < thr
        i300 = int(np.argmin(np.abs(Ts - 300.0)))
        for i in range(i300, 0, -1):          # cold side
            if below[i - 1] and not below[i]:
                lo = float(np.interp(thr, [accs[i - 1], accs[i]],
                                     [Ts[i - 1], Ts[i]]))
                break
        else:
            lo = float("nan") if not below[0] else lo
        for i in range(i300, len(Ts) - 1):    # hot side
            if below[i + 1] and not below[i]:
                hi = float(np.interp(thr, [accs[i + 1], accs[i]],
                                     [Ts[i + 1], Ts[i]]))
                break
        else:
            hi = float("nan") if not below[-1] else hi
        return lo, hi

    windows = {}
    for scen in ("no_recal", "slope_only"):
        for drop in ACC_DROPS:
            lo, hi = crossings(scen, drop)
            windows[f"{scen}_{int(drop * 100)}pp"] = [lo, hi]
            print(f"window {scen} -{int(drop * 100)}pp: "
                  f"[{lo:.1f}, {hi:.1f}] K", flush=True)

    # trim spec: shift at the slope_only 1pp window edges must fit the DAC
    lo1, hi1 = windows["slope_only_1pp"]
    edge_shift_mV = {
        "cold": float(ts.vth_shift(lo1, stack)) * 1e3 if np.isfinite(lo1) else None,
        "hot": float(ts.vth_shift(hi1, stack)) * 1e3 if np.isfinite(hi1) else None,
    }
    # refresh cadence: |dT| at which the UNCORRECTED shift costs 1pp
    nr_lo, nr_hi = windows["no_recal_1pp"]
    dvth_per_K = float((ts.vth_shift(310.0, stack)
                        - ts.vth_shift(290.0, stack)) / 20.0) * 1e3

    tau_ratio_350 = float(np.interp(350.0, T_dense, tau_corr / tau_simp))
    tau_ratio_400 = float(np.interp(400.0, T_dense, tau_corr / tau_simp))
    summary = dict(
        acc_ref_300K=acc_ref, windows_K=windows,
        dvth_per_K_mV=dvth_per_K,
        no_recal_1pp_halfwidth_K=[300.0 - nr_lo, nr_hi - 300.0],
        trim_edge_shift_mV=edge_shift_mV,
        trim_lsb_mV=list(TRIM_LSB_MV),
        trim_codes_at_slope_only_edges=[
            abs(v) / TRIM_LSB_MV[1] if v is not None else None
            for v in edge_shift_mV.values()],
        rc_clock_rescale_vs_simplified={"350K": tau_ratio_350,
                                        "400K": tau_ratio_400},
        caliber="single 300 K anchor + platform scaling laws; frozen BN; "
                "C2C athermal; slope_only doubles as (pessimistic + trim "
                "refresh) and (optimistic athermal threshold, no recal)",
    )
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=1),
                                          encoding="utf-8")

    # ---- figure -----------------------------------------------------------
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
    ax2.set_ylabel(r"$V_{th}$ shift (mV)", color="tab:red")
    ax2.tick_params(axis="y", labelcolor="tab:red")
    ax.set_xlabel("ambient temperature (K)")
    ax.set_ylabel("ratio to 300 K anchor")
    ax.set_title("scaling chain through 81%-compensated K_eff")
    ax.legend(fontsize=10, loc="lower left")

    ax = axes[1]
    for scen, color, label in (
            ("no_recal", "tab:red", "no recalibration (pessimistic chain)"),
            ("slope_only", "tab:blue",
             "trim-refreshed / athermal-threshold")):
        pts = sorted([(r["T_K"], r["acc"]) for r in rows
                      if r["scenario"] == scen])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-", color=color,
                lw=2, ms=4, label=label)
    for drop, ls in zip(ACC_DROPS, ("--", ":")):
        ax.axhline(acc_ref - drop, color="0.4", lw=1, ls=ls)
        ax.text(402, acc_ref - drop, f"-{int(drop * 100)}pp", fontsize=10,
                va="bottom", color="0.3")
    if np.isfinite(nr_lo) and np.isfinite(nr_hi):
        ax.axvspan(nr_lo, nr_hi, color="tab:red", alpha=0.08)
    ax.axvline(300.0, color="0.6", lw=0.8, ls=":")
    ax.set_xlabel("ambient temperature (K)")
    ax.set_ylabel(f"MNIST accuracy (T={T_READS} reads)")
    ax.set_ylim(0.05, 1.0)
    ax.set_title("common-mode drift: deployed-network window")
    ax.legend(fontsize=10, loc="lower center")

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
