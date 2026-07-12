#!/usr/bin/env python3
"""T2-3: counting (popcount) RC readout vs SAR -- the fourth axis of C3.

rc_isoenergy.py optimized {N, M, b} with an analog-sum + SAR readout on the
NOISELESS mean-field state -- implicitly an infinite ensemble. The PBNN mode
of the same array reads columns with a 1-bit sense + popcount counter, so
the obvious unification question is whether the RC mode can reuse that
counting periphery instead of adding a SAR ADC.

This bench runs the reservoir in its physical stochastic mode (each logical
node = an ensemble of E telegraph devices, exp16 machinery, correlations
across steps preserved) and compares three peripheries reading the SAME
physical column:

  counting-1   one strobe at window end: exact popcount of the E device
               states, no time integration.  E_read = E (E_comp + E_cnt)
  counting-S   a strobe per micro-step (S = substeps): the counter output
               EQUALS the analog integrator value, losslessly digital.
               E_read = S E (E_comp + E_cnt)
  SAR-b        passive analog integration over the window (free), one b-bit
               conversion.  E_read = b E_comp + 2^b E_capDAC0

The integration-window rule says counting-S buys almost nothing over
counting-1: with dt = 25 ns and tau = 22-68 ns a device contributes
N_eff ~ 1 + dt/(2 tau) = 1.18-1.57 independent samples per window, so
window-internal time averaging is dead and resolution must come from the
ensemble: sigma = 1/(2 sqrt(E)), b_eff = 0.5 log2(E), every extra bit
costs 4x devices. The SAR gets the (tiny) integration gain for free and
quantizes with step below the shot noise at b* = ceil(b_eff) + 1.

Energy constants: repo's extracted/derived sky130 numbers -- E_comp = 48 fJ
(post-layout StrongARM, sa_postlayout.py), E_cnt = 19.4 fJ per counter
increment (dac_counter_energy.py, ngspice), E_capDAC0 = 1.1 fJ, E_dev =
5 fJ/device-step (order of magnitude). Ratios are the claim, not joules.

Side finding vs rc_isoenergy.py: its noiseless-signal MC (~4.5 at N = 240)
is an infinite-ensemble ceiling; at physical E the ensemble shot noise --
not ADC bits -- is the binding constraint on MC.

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
SAR_BITS = (2, 3, 4, 5, 6, 8)


def e_sar_fJ(b: int) -> float:
    return b * E_COMP_fJ + E_CAPDAC0_fJ * (2 ** b)


def e_count_fJ(E: int, strobes: int = 1) -> float:
    return strobes * E * (E_COMP_fJ + E_CNT_fJ)


def sar_quant(X: np.ndarray, bits: int) -> np.ndarray:
    vfs = float(np.max(np.abs(X))) * 1.0001 + 1e-12
    step = 2 * vfs / (2 ** bits - 1)
    return np.clip(np.round(X / step) * step, -vfs, vfs)


def run_dual_readout(res: SMTJReservoir, u: np.ndarray):
    """One stochastic trajectory; return (X_int, X_last) after washout.

    X_int  -- micro-step time-averaged ensemble mean (analog integrator /
              counting-S), the state that also feeds the recurrent path,
              identical to SMTJReservoir.run().
    X_last -- ensemble fraction at the final micro-step only (counting-1).
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
        x_prev = x_int
        Xi.append(x_int)
        Xl.append(x_last)
    return np.array(Xi)[WASHOUT:], np.array(Xl)[WASHOUT:]


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 13,
                         "axes.labelsize": 14, "axes.titlesize": 14})

    taus = {"tau_0V_ns": float(relaxation_time(0.0)) * 1e9, "tau_op_ns": 22.0}
    n_eff = {k: 1.0 + DT / (2.0 * v * 1e-9) for k, v in taus.items()}
    print(f"window-tau rule: dt = {DT*1e9:.0f} ns;",
          ", ".join(f"{k}={v:.1f} -> N_eff={n_eff[k]:.2f}"
                    for k, v in taus.items()), flush=True)

    u = tasks.memory_capacity_inputs(1200, seed=2)
    ua = u[WASHOUT:]
    mf_cfg = ReservoirConfig(n_nodes=N_NODES, mode="meanfield",
                             effective_spectral_radius=ESR,
                             effective_input_scale=INPUT_SCALE, dt=DT,
                             substeps=SUBSTEPS, seed=1)
    X_mf = SMTJReservoir(mf_cfg, 1).run(u, washout=WASHOUT)
    mc_mf, _ = memory_capacity(X_mf, ua, max_delay=MAX_DELAY)
    print(f"mean-field (infinite-ensemble) reference MC = {mc_mf:.2f}",
          flush=True)
    rows = []
    for E in ENSEMBLES:
        cfg = ReservoirConfig(n_nodes=N_NODES, mode="stochastic", ensemble=E,
                              effective_spectral_radius=ESR,
                              effective_input_scale=INPUT_SCALE, dt=DT,
                              substeps=SUBSTEPS, seed=1)
        res = SMTJReservoir(cfg, n_inputs=1)
        X_int, X_last = run_dual_readout(res, u)
        S = cfg.substeps
        evo = N_NODES * E * E_DEV_fJ

        mc1, _ = memory_capacity(X_last, ua, max_delay=MAX_DELAY)
        rows.append(dict(readout="counting-1", E=E, b=None, MC=float(mc1),
                         E_read_fJ=N_NODES * e_count_fJ(E, 1),
                         E_tot_fJ=evo + N_NODES * e_count_fJ(E, 1)))
        mcS, _ = memory_capacity(X_int, ua, max_delay=MAX_DELAY)
        rows.append(dict(readout="counting-S", E=E, b=None, MC=float(mcS),
                         E_read_fJ=N_NODES * e_count_fJ(E, S),
                         E_tot_fJ=evo + N_NODES * e_count_fJ(E, S)))
        for b in SAR_BITS:
            mcb, _ = memory_capacity(sar_quant(X_int, b), ua,
                                     max_delay=MAX_DELAY)
            rows.append(dict(readout="sar", E=E, b=b, MC=float(mcb),
                             E_read_fJ=N_NODES * e_sar_fJ(b),
                             E_tot_fJ=evo + N_NODES * e_sar_fJ(b)))
        b_star = int(np.ceil(0.5 * np.log2(E))) + 1
        mc_bs = next(r["MC"] for r in rows
                     if r["readout"] == "sar" and r["E"] == E
                     and r["b"] == min(SAR_BITS, key=lambda x: abs(x - b_star)))
        print(f"E={E:4d}: counting-1 MC={mc1:.2f} @ {e_count_fJ(E, 1):.0f} fJ"
              f" | counting-S MC={mcS:.2f} @ {e_count_fJ(E, S):.0f} fJ"
              f" | SAR b*={b_star} MC={mc_bs:.2f} @ {e_sar_fJ(b_star):.0f} fJ"
              f" -> counting-1/SAR = "
              f"{e_count_fJ(E, 1) / e_sar_fJ(b_star):.1f}x readout", flush=True)

    # iso-information summary at the deterministic b* rule
    iso = []
    for E in ENSEMBLES:
        b_star = int(np.ceil(0.5 * np.log2(E))) + 1
        b_near = min(SAR_BITS, key=lambda x: abs(x - b_star))
        c1 = next(r for r in rows if r["readout"] == "counting-1"
                  and r["E"] == E)
        cS = next(r for r in rows if r["readout"] == "counting-S"
                  and r["E"] == E)
        sb = next(r for r in rows if r["readout"] == "sar" and r["E"] == E
                  and r["b"] == b_near)
        iso.append(dict(E=E, b_eff=0.5 * np.log2(E), b_star=b_star,
                        mc_counting1=c1["MC"], mc_countingS=cS["MC"],
                        mc_sar_bstar=sb["MC"],
                        integration_gain=cS["MC"] - c1["MC"],
                        ratio_readout_c1=c1["E_read_fJ"] / sb["E_read_fJ"],
                        ratio_total_c1=c1["E_tot_fJ"] / sb["E_tot_fJ"]))

    # ---- figure -------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax = axes[0]
    Es = np.array(ENSEMBLES, dtype=float)
    for name, color, marker in (("counting-1", "tab:red", "o"),
                                ("counting-S", "tab:orange", "s")):
        pts = [next(r for r in rows if r["readout"] == name and r["E"] == E)
               for E in ENSEMBLES]
        ax.plot(Es, [p["MC"] for p in pts], marker + "-", color=color, lw=2,
                ms=6, label=name)
    sar_star = [next(r for r in rows if r["readout"] == "sar" and r["E"] == E
                     and r["b"] == min(SAR_BITS, key=lambda x: abs(
                         x - (int(np.ceil(0.5 * np.log2(E))) + 1))))
                for E in ENSEMBLES]
    ax.plot(Es, [p["MC"] for p in sar_star], "^-", color="tab:blue", lw=2,
            ms=6, label="SAR at b* (shot-noise matched)")
    ax.set_xscale("log", base=2)
    ax.set_xlabel("ensemble size E per node")
    ax.set_ylabel(f"memory capacity (N={N_NODES}, stochastic)")
    ax.set_title("shot noise, not bits, limits MC")
    ax.legend(fontsize=10)

    ax = axes[1]
    rr = [i["ratio_readout_c1"] for i in iso]
    rt = [i["ratio_total_c1"] for i in iso]
    ax.loglog(Es, rr, "o-", color="tab:red", lw=2,
              label="readout energy, counting-1 / SAR-b*")
    ax.loglog(Es, rt, "s--", color="tab:orange", lw=2, label="total energy")
    ax.axhline(1.0, color="0.5", lw=1)
    for x, i in zip(Es, iso):
        ax.annotate(f"$b_{{eff}}$={i['b_eff']:.1f}", (x, i["ratio_readout_c1"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=10)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("ensemble size E per node")
    ax.set_ylabel("counting / SAR energy ratio")
    ax.set_title("price of reusing the popcount periphery")
    ax.legend(fontsize=10)
    fig.tight_layout()
    fig_path = REPO / "figures" / "31_rc_counting_readout.png"
    fig.savefig(fig_path, dpi=200, bbox_inches="tight")

    i96 = next(i for i in iso if i["E"] == 96)
    concl = (
        "Counting readout reuses the PBNN popcount periphery and reads the "
        "ensemble losslessly, but pays per-device sensing energy: at the "
        "canonical E = 96 a single-strobe popcount costs %.0fx the "
        "shot-noise-matched SAR conversion (b* = %d) for %s MC "
        "(counting-1 %.2f vs SAR %.2f; the single strobe also FORFEITS the "
        "window-integration gain of +%.2f MC that the analog integrator "
        "collects passively, N_eff <= %.2f at dt = 25 ns). Every effective "
        "bit costs 4x devices AND 4x sensing energy (b_eff = 0.5 log2 E), "
        "while the SAR price is b-linear. Verdict: the seemingly obvious "
        "'reuse the PBNN counters for RC' route is energetically excluded "
        "whenever a column-shared SAR is available; it survives only as the "
        "area-minimal single-periphery option. Side finding: the mean-field "
        "MC at this same operating point (%.2f) is an infinite-ensemble "
        "ceiling; at physical E the ensemble noise -- acting through "
        "readout AND recurrence -- binds MC, not ADC resolution." % (
            i96["ratio_readout_c1"], i96["b_star"],
            "comparable" if abs(i96["mc_counting1"] - i96["mc_sar_bstar"])
            < 0.15 else "lower",
            i96["mc_counting1"], i96["mc_sar_bstar"],
            i96["integration_gain"], max(n_eff.values()), mc_mf))
    print("\n" + "=" * 92 + "\n" + concl + "\n" + "=" * 92)

    summ = dict(constants_fJ=dict(E_dev=E_DEV_fJ, E_comp=E_COMP_fJ,
                                  E_cnt=E_CNT_fJ, E_capDAC0=E_CAPDAC0_fJ),
                dt_ns=DT * 1e9, taus_ns=taus, n_eff_window=n_eff,
                n_nodes=N_NODES, substeps=SUBSTEPS, mc_meanfield_ref=float(mc_mf),
                rows=rows,
                iso_information=iso, conclusion=concl)
    (HERE / "rc_counting_readout_summary.json").write_text(
        json.dumps(summ, indent=1), encoding="utf-8")
    print(f"figure: {fig_path}\nwrote rc_counting_readout_summary.json")


if __name__ == "__main__":
    main()
