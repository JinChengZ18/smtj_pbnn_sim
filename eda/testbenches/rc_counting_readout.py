#!/usr/bin/env python3
"""T2-3: counting (popcount) RC readout vs SAR -- the fourth axis of C3.

rc_isoenergy.py optimized {N, M, b} with an analog-sum + SAR readout on the
NOISELESS mean-field state -- implicitly an infinite ensemble. The PBNN mode
of the same array reads columns with a 1-bit sense + popcount counter, so
the obvious unification question is whether the RC mode can reuse that
counting periphery instead of adding a SAR ADC.

This bench runs the reservoir in its physical stochastic mode (each logical
node = an ensemble of E telegraph devices, exp16 machinery, correlations
across steps preserved) and compares peripheries reading the SAME column:

  counting-1    one strobe at window end, recurrence driven by the analog-
                integrated state (a HYBRID: the integrator periphery is
                present but unbilled).       E_read = E (E_comp + E_cnt)
  counting-1sc  the honest single-periphery system: the recurrent path is
                driven by the SAME single-strobe popcount the readout
                uses (feedback = x_last).    E_read = E (E_comp + E_cnt)
  counting-S    a strobe per micro-step (S = substeps): counter output
                EQUALS the analog integrator value, losslessly digital.
                E_read = S E (E_comp + E_cnt)
  SAR-b         passive analog integration over the window, one b-bit
                conversion.  E_read = b E_comp + 2^b E_capDAC0
                (the integrator/S&H front-end is NOT billed, mirroring
                rc_isoenergy.py -- stated, and it biases AGAINST the
                verdict's direction by at most the comparator scale)

Plus a noise-channel ablation: recurrence driven by the NOISELESS
mean-field state while the readout still samples the physical device
pool -- isolating readout-channel noise from recurrence-channel noise.

The integration-window rule says counting-S buys little over counting-1:
with dt = 25 ns and tau = 22-68 ns a device contributes N_eff ~ 1 +
dt/(2 tau) = 1.18-1.57 independent samples per window, so window-internal
time averaging is nearly dead and resolution must come from the ensemble:
sigma = 1/(2 sqrt(E)), b_eff = 0.5 log2(E), every extra bit costs 4x
devices. The SAR quantizes with step below the shot noise at
b* = ceil(b_eff) + 1 (all b* values are in the simulated grid).

Energy constants: E_comp = 48 fJ (extracted post-layout StrongARM,
sa_postlayout.py); E_cnt = 19.4 fJ per counter increment -- a sky130
STANDARD-CELL CAPACITANCE ESTIMATE (~2x uncertainty pending Liberty),
dac_counter_energy.py (its ngspice transient grounds only the DAC analog
core, not this number); E_capDAC0 = 1.1 fJ; E_dev = 5 fJ/device-step
(order of magnitude). Counting billing is worst-case (every strobe
increments); average-increment billing (~E/2 increments at p ~ 0.5) is
reported as a sensitivity. Ratios are the claim, not joules.

Estimator noise: every MC is reported as mean +- half-range over 3
reservoir seeds.

Run: python eda/testbenches/rc_counting_readout.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from smtj_pbnn_sim.device.telegraph import relaxation_time
from smtj_pbnn_sim.reservoir import (ReservoirConfig, SMTJReservoir,
                                     memory_capacity, tasks)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MAX_DELAY = 25
N_NODES = 100                  # canonical exp14/16 operating point
DT = 25e-9
SUBSTEPS = 25
INPUT_SCALE = 2.0
ESR = 0.5
WASHOUT = 100
E_DEV_fJ = 5.0
E_COMP_fJ = 48.0
E_CNT_fJ = 19.44
E_CAPDAC0_fJ = 1.1
ENSEMBLES = (16, 64, 96, 256, 1024)
SAR_BITS = (2, 3, 4, 5, 6, 7, 8)
SEEDS = (1, 2, 3)
ABLATION_E = (16, 96, 1024)


def e_sar_fJ(b: int) -> float:
    return b * E_COMP_fJ + E_CAPDAC0_fJ * (2 ** b)


def e_count_fJ(E: int, strobes: int = 1, avg_inc: bool = False) -> float:
    cnt = E_CNT_fJ * (0.5 if avg_inc else 1.0)
    return strobes * E * (E_COMP_fJ + cnt)


def b_star_of(E: int) -> int:
    return int(np.ceil(0.5 * np.log2(E))) + 1


def sar_quant(X: np.ndarray, bits: int) -> np.ndarray:
    vfs = float(np.max(np.abs(X))) * 1.0001 + 1e-12
    step = 2 * vfs / (2 ** bits - 1)
    return np.clip(np.round(X / step) * step, -vfs, vfs)


def run_traj(res: SMTJReservoir, u: np.ndarray, feedback: str):
    """One stochastic trajectory; returns (X_int, X_last) after washout.

    feedback = 'int'       recurrence sees the integrated state (analog
                           recurrent path; SMTJReservoir.run() dynamics)
             = 'last'      recurrence sees the single-strobe popcount
                           (self-consistent counting-only periphery)
             = 'meanfield' recurrence sees the noiseless mean-field state
                           (ablation: readout-channel noise only)
    """
    cfg = res.cfg
    u2 = u[:, None] if u.ndim == 1 else u
    micro_dt = cfg.dt / cfg.substeps
    x_prev = np.zeros(cfg.n_nodes)
    Xi, Xl = [], []
    for t in range(u2.shape[0]):
        V = res._node_voltage(u2[t], x_prev)
        V_full = np.repeat(V, cfg.ensemble)
        acc = np.zeros(cfg.n_nodes * cfg.ensemble)
        last = None
        for _ in range(cfg.substeps):
            last = res.array.step(V_full, micro_dt)
            acc += last
        x_int = (acc / cfg.substeps).reshape(cfg.n_nodes, cfg.ensemble).mean(1)
        x_last = last.reshape(cfg.n_nodes, cfg.ensemble).mean(1)
        if feedback == "int":
            x_prev = x_int
        elif feedback == "last":
            x_prev = x_last
        else:
            x_prev = res._step_meanfield(V, x_prev)
        Xi.append(x_int)
        Xl.append(x_last)
    return np.array(Xi)[WASHOUT:], np.array(Xl)[WASHOUT:]


def mstat(vals) -> dict:
    vals = list(vals)
    return dict(mean=float(np.mean(vals)),
                half_range=float((max(vals) - min(vals)) / 2.0))


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 13,
                         "axes.labelsize": 14, "axes.titlesize": 14})

    taus = {"tau_0V_ns": float(relaxation_time(0.0)) * 1e9, "tau_op_ns": 22.0}
    n_eff = {k: 1.0 + DT / (2.0 * v * 1e-9) for k, v in taus.items()}
    print(f"window-tau rule: dt = {DT * 1e9:.0f} ns;",
          ", ".join(f"{k}={v:.1f} -> N_eff={n_eff[k]:.2f}"
                    for k, v in taus.items()), flush=True)

    u = tasks.memory_capacity_inputs(1200, seed=2)
    ua = u[WASHOUT:]

    def make_cfg(mode, E, seed):
        return ReservoirConfig(n_nodes=N_NODES, mode=mode, ensemble=E,
                               effective_spectral_radius=ESR,
                               effective_input_scale=INPUT_SCALE, dt=DT,
                               substeps=SUBSTEPS, seed=seed)

    mc_mf = []
    for seed in SEEDS:
        X_mf = SMTJReservoir(make_cfg("meanfield", 24, seed), 1).run(
            u, washout=WASHOUT)
        mc_mf.append(memory_capacity(X_mf, ua, max_delay=MAX_DELAY)[0])
    mf = mstat(mc_mf)
    print(f"mean-field (infinite-ensemble) reference MC = "
          f"{mf['mean']:.2f} +- {mf['half_range']:.2f}", flush=True)

    rows = []
    for E in ENSEMBLES:
        per_seed = {"counting-1": [], "counting-1sc": [], "counting-S": [],
                    **{f"sar{b}": [] for b in SAR_BITS}}
        for seed in SEEDS:
            res = SMTJReservoir(make_cfg("stochastic", E, seed), n_inputs=1)
            X_int, X_last = run_traj(res, u, feedback="int")
            per_seed["counting-1"].append(
                memory_capacity(X_last, ua, max_delay=MAX_DELAY)[0])
            per_seed["counting-S"].append(
                memory_capacity(X_int, ua, max_delay=MAX_DELAY)[0])
            for b in SAR_BITS:
                per_seed[f"sar{b}"].append(
                    memory_capacity(sar_quant(X_int, b), ua,
                                    max_delay=MAX_DELAY)[0])
            res_sc = SMTJReservoir(make_cfg("stochastic", E, seed),
                                   n_inputs=1)
            _, X_last_sc = run_traj(res_sc, u, feedback="last")
            per_seed["counting-1sc"].append(
                memory_capacity(X_last_sc, ua, max_delay=MAX_DELAY)[0])
        S = SUBSTEPS
        evo = N_NODES * E * E_DEV_fJ
        for name, strobes in (("counting-1", 1), ("counting-1sc", 1),
                              ("counting-S", S)):
            st = mstat(per_seed[name])
            rows.append(dict(readout=name, E=E, b=None, MC=st["mean"],
                             MC_half_range=st["half_range"],
                             E_read_fJ=N_NODES * e_count_fJ(E, strobes),
                             E_read_avg_fJ=N_NODES * e_count_fJ(
                                 E, strobes, avg_inc=True),
                             E_tot_fJ=evo + N_NODES * e_count_fJ(E, strobes)))
        for b in SAR_BITS:
            st = mstat(per_seed[f"sar{b}"])
            rows.append(dict(readout="sar", E=E, b=b, MC=st["mean"],
                             MC_half_range=st["half_range"],
                             E_read_fJ=N_NODES * e_sar_fJ(b),
                             E_read_avg_fJ=N_NODES * e_sar_fJ(b),
                             E_tot_fJ=evo + N_NODES * e_sar_fJ(b)))
        bs = b_star_of(E)
        get = lambda nm, bb=None: next(
            r for r in rows if r["readout"] == nm and r["E"] == E
            and (bb is None or r["b"] == bb))
        print(f"E={E:4d}: c1 {get('counting-1')['MC']:.2f} | "
              f"c1sc {get('counting-1sc')['MC']:.2f} | "
              f"cS {get('counting-S')['MC']:.2f} | "
              f"SAR b*={bs} {get('sar', bs)['MC']:.2f} "
              f"(+-{get('sar', bs)['MC_half_range']:.2f}) -> "
              f"c1/SAR = {e_count_fJ(E, 1) / e_sar_fJ(bs):.1f}x readout "
              f"({e_count_fJ(E, 1, avg_inc=True) / e_sar_fJ(bs):.1f}x "
              f"avg-billing)", flush=True)

    # noise-channel ablation: readout noise only (mean-field recurrence)
    ablation = {}
    for E in ABLATION_E:
        vals = []
        for seed in SEEDS:
            res = SMTJReservoir(make_cfg("stochastic", E, seed), n_inputs=1)
            X_int_ro, _ = run_traj(res, u, feedback="meanfield")
            vals.append(memory_capacity(X_int_ro, ua,
                                        max_delay=MAX_DELAY)[0])
        both = next(r for r in rows if r["readout"] == "counting-S"
                    and r["E"] == E)
        ablation[str(E)] = dict(
            readout_noise_only=mstat(vals),
            noise_through_both=dict(mean=both["MC"],
                                    half_range=both["MC_half_range"]))
        print(f"ablation E={E}: readout-noise-only MC = "
              f"{np.mean(vals):.2f} +- {(max(vals) - min(vals)) / 2:.2f} vs "
              f"noise-through-both {both['MC']:.2f}", flush=True)

    iso = []
    for E in ENSEMBLES:
        bs = b_star_of(E)
        c1 = next(r for r in rows if r["readout"] == "counting-1"
                  and r["E"] == E)
        c1sc = next(r for r in rows if r["readout"] == "counting-1sc"
                    and r["E"] == E)
        cS = next(r for r in rows if r["readout"] == "counting-S"
                  and r["E"] == E)
        sb = next(r for r in rows if r["readout"] == "sar" and r["E"] == E
                  and r["b"] == bs)
        iso.append(dict(E=E, b_eff=0.5 * np.log2(E), b_star=bs,
                        mc_counting1=c1["MC"], mc_counting1sc=c1sc["MC"],
                        mc_countingS=cS["MC"], mc_sar_bstar=sb["MC"],
                        ratio_readout_c1=c1["E_read_fJ"] / sb["E_read_fJ"],
                        ratio_readout_c1_avg=c1["E_read_avg_fJ"]
                        / sb["E_read_fJ"],
                        ratio_total_c1=c1["E_tot_fJ"] / sb["E_tot_fJ"]))

    # ---- figure -------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax = axes[0]
    Es = np.array(ENSEMBLES, dtype=float)
    for name, color, marker, label in (
            ("counting-1sc", "tab:red", "o", "counting (single periphery)"),
            ("counting-S", "tab:orange", "s", "integrating counter"),):
        pts = [next(r for r in rows if r["readout"] == name and r["E"] == E)
               for E in ENSEMBLES]
        ax.errorbar(Es, [p["MC"] for p in pts],
                    yerr=[p["MC_half_range"] for p in pts], marker=marker,
                    color=color, lw=2, ms=6, capsize=3, label=label)
    sar_star = [next(r for r in rows if r["readout"] == "sar"
                     and r["E"] == E and r["b"] == b_star_of(E))
                for E in ENSEMBLES]
    ax.errorbar(Es, [p["MC"] for p in sar_star],
                yerr=[p["MC_half_range"] for p in sar_star], marker="^",
                color="tab:blue", lw=2, ms=6, capsize=3,
                label="SAR at b* (shot-noise matched)")
    ax.axhline(mf["mean"], color="0.5", lw=1.2, ls="--")
    ax.text(Es[0], mf["mean"] + 0.05, "mean-field ceiling", fontsize=10,
            color="0.35")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("ensemble size E per node")
    ax.set_ylabel(f"memory capacity (N={N_NODES}, stochastic)")
    ax.set_title("ensemble noise, not bits, limits MC")
    ax.legend(fontsize=10)

    ax = axes[1]
    rr = [i["ratio_readout_c1"] for i in iso]
    rr_avg = [i["ratio_readout_c1_avg"] for i in iso]
    rt = [i["ratio_total_c1"] for i in iso]
    ax.loglog(Es, rr, "o-", color="tab:red", lw=2,
              label="readout energy (worst-case billing)")
    ax.loglog(Es, rr_avg, "o--", color="tab:red", lw=1.2, alpha=0.6,
              label="readout energy (avg-increment billing)")
    ax.loglog(Es, rt, "s--", color="tab:orange", lw=2, label="total energy")
    ax.axhline(1.0, color="0.5", lw=1)
    for x, i in zip(Es, iso):
        ax.annotate(f"$b_{{eff}}$={i['b_eff']:.1f}",
                    (x, i["ratio_readout_c1"]), textcoords="offset points",
                    xytext=(6, 6), fontsize=10)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("ensemble size E per node")
    ax.set_ylabel("counting / SAR energy ratio")
    ax.set_title("price of reusing the popcount periphery")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig_path = REPO / "figures" / "31_rc_counting_readout.png"
    fig.savefig(fig_path, dpi=200, bbox_inches="tight")

    i96 = next(i for i in iso if i["E"] == 96)
    ab96 = ablation["96"]
    concl = (
        "Counting readout reuses the PBNN popcount periphery and reads the "
        "ensemble losslessly, but pays per-device sensing energy: at the "
        "canonical E = 96 the honest single-periphery system (recurrence "
        "AND readout from one popcount strobe) reaches MC %.2f vs %.2f for "
        "the shot-noise-matched SAR (b* = %d) at %.0fx the readout energy "
        "(%.0fx under average-increment billing; the SAR's unbilled "
        "integrator front-end would only widen the gap). Every effective "
        "bit costs 4x devices AND 4x sensing energy (b_eff = 0.5 log2 E), "
        "while the SAR price is b-linear. Verdict: the seemingly obvious "
        "'reuse the PBNN counters for RC' route is energetically excluded "
        "whenever a column-shared SAR is available; it survives only as "
        "the area-minimal single-periphery option, and even there gives "
        "up the integration gain. Noise-channel ablation at E = 96: "
        "readout-noise-only MC %.2f +- %.2f vs noise-through-both "
        "%.2f +- %.2f -- the recurrence channel's contribution is within "
        "estimator noise; ensemble noise binds MC through the READOUT "
        "channel (mean-field ceiling %.2f +- %.2f)." % (
            i96["mc_counting1sc"], i96["mc_sar_bstar"], i96["b_star"],
            i96["ratio_readout_c1"], i96["ratio_readout_c1_avg"],
            ab96["readout_noise_only"]["mean"],
            ab96["readout_noise_only"]["half_range"],
            ab96["noise_through_both"]["mean"],
            ab96["noise_through_both"]["half_range"],
            mf["mean"], mf["half_range"]))
    print("\n" + "=" * 92 + "\n" + concl + "\n" + "=" * 92)

    summ = dict(constants_fJ=dict(
                    E_dev=E_DEV_fJ, E_comp=E_COMP_fJ, E_cnt=E_CNT_fJ,
                    E_capDAC0=E_CAPDAC0_fJ,
                    e_cnt_caliber="sky130 standard-cell capacitance "
                                  "estimate, ~2x uncertainty pending "
                                  "Liberty (dac_counter_energy.py; its "
                                  "ngspice grounds only the DAC analog "
                                  "core)"),
                dt_ns=DT * 1e9, taus_ns=taus, n_eff_window=n_eff,
                n_nodes=N_NODES, substeps=SUBSTEPS, seeds=list(SEEDS),
                mc_meanfield_ref=mf, rows=rows, ablation=ablation,
                iso_information=iso, conclusion=concl)
    (HERE / "rc_counting_readout_summary.json").write_text(
        json.dumps(summ, indent=1), encoding="utf-8")
    print(f"figure: {fig_path}\nwrote rc_counting_readout_summary.json")


if __name__ == "__main__":
    main()
