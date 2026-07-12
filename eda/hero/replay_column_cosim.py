#!/usr/bin/env python3
"""T3-5: deterministic-replay column-level co-simulation (behavioral vs circuit).

The architecture keeps the stochastic weight bits in the harness RNG by
design; the SAME drawn column states are replayed through (a) the
behavioral popcount decision and (b) a full sky130 transient of the
readout chain -- what this validates is the JOINT EFFECT OF THE READOUT
CHAIN (bit-line IR, transimpedance mapping, StrongARM offset/regeneration,
settling), not the write stochasticity itself.

Column (C1 architecture, N = 64): each weight cell is a differential MTJ
pair (R_P, R_AP) assigned by the drawn bit s_i (diff_column convention,
x_i = +1), tapping two bit-lines with per-segment extracted wire R (met1
0.125 ohm/sq at 0.23 um width, 2 um pitch -> 1.09 ohm/segment) and 0.4 fF
tap capacitance. The lines terminate in a VIRTUAL-GROUND transimpedance
stage (behavioral op-amp, gain 2e4, feedback R_TI = V_in/(2 PC_FS LSB_I),
PC_FS = 3 sqrt(N) = 24 -> 2450 ohm) followed by the sky130 StrongARM SA
(run_readout_frontend netlist, transistor level). The virtual ground is
REQUIRED, not a convenience: the column's Norton impedance is
state-dependent, 98-175 ohm (~105 ohm at the drawn state mix; 64 cells
of 4.9-9.8 kohm in parallel), so a passive resistor to vcm collapses
both the common mode and the popcount slope (measured during bring-up:
effective transimpedance ~110 ohm, ~0.6 mV/pc against a 9.21 mV SA
offset). The column's COMMON-MODE current (~0.4 mA/side) must not flow
through the feedback either -- without cancellation it drags the TIA
output to -0.09 V and cuts the SA input pair off (first-audit finding:
the SA then 'decides' on microvolt leakage residues) -- so each
virtual-ground node carries a matched reference-column cancellation
source I_cm = N (G_P+G_AP)/2 (VR/2), the standard CIM dummy-column
technique. Modeling boundary: the op-amp and the cancellation source
are behavioral; the noisy decision element (SA offset/regeneration)
stays transistor-level.
The BN threshold theta is injected as a differential reference current
at (theta+1) LSB_I into the virtual-ground nodes, with theta chosen even
and near E[pc] so trials cluster at the decision boundary (theta+1 odd,
so the even-parity popcount can never tie).

Per trial: draw s ~ Bernoulli(p_i), set 128 resistor values, settle 5 ns,
clock the SA, read v(outp)-v(outn). Behavioral prediction: sign(pc -
(theta+1)) with pc = sum s_i. Agreement is checked exactly per trial
(deterministic replay); the analog-popcount residual distribution gets a
LILLIEFORS normality check about its fitted mean (the systematic line-IR
bias is a separate, reported quantity -- a zero-error null would be
trivially rejected); the far-end bit-line IR drop is MEASURED (upgrading
the 'negligible read-path drop' assertion). Offset variants: 0 mV
(typical) and the extracted 9.21 mV 1-sigma StrongARM offset as a
worst-case dc source; variants use independent state draws. Scope
limits, stated: all trials come from ONE drawn column instance
(p ~ U[0.1, 0.9], seed fixed) with theta deliberately placed at E[pc]
(near-threshold stress); the recalibrated agreement is an output-node
projection of a threshold shift (justified when the SA resolves the
shifted margin), not a re-simulated threshold current.

MUST RUN IN WSL (native ngspice + sky130):
  wsl -d Ubuntu-24.04-EDA -- bash -lc \
    'cd "/mnt/d/Documents/Graduation Project-2026/04PBNNSim/smtj_pbnn_sim" \
     && python3 eda/hero/replay_column_cosim.py [--smoke]'
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LIB = "/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
RUN = HERE / "_replay_column.spice"

N = 64
RP, TMR, VR = 4900.0, 1.0, 0.1
GP, GAP = 1.0 / RP, 1.0 / (RP * (1.0 + TMR))
LSB_I = (VR / 2.0) * (GP - GAP)          # 5.102 uA per popcount unit
PC_FS = 3.0 * np.sqrt(N)                  # slope-matched full scale (C1 law)
V_IN = 0.6                                # SA differential input budget [V]
R_TI = V_IN / (2.0 * PC_FS * LSB_I)
R_SEG = 0.125 / 0.23 * 2.0                # met1 sheet R / width * 2 um pitch
C_TAP = 0.4e-15
VCM = 0.9
SEED = 20260713
TRIALS_PER_DECK = 100
N_DECKS = 6
T_SETTLE = 5e-9                           # BL settle before SA clock
T_CLK = 1e-9                              # SA clock edge inside the window


def sa_core(os_mV: float) -> str:
    """StrongARM SA + offset source (run_readout_frontend device sizes)."""
    return f"""Vos g1 np DC {os_mV * 1e-3:.6g}
Vg2 g2 nn DC 0
XMtail ntail clk vss   vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM1    da    g1  ntail vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM2    db    g2  ntail vss sky130_fd_pr__nfet_01v8 W=4 L=0.15
XM3    outn  outp da   vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM4    outp  outn db   vss sky130_fd_pr__nfet_01v8 W=2 L=0.15
XM5    outn  outp vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XM6    outp  outn vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp1   outp  clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp2   outn  clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp3   da    clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
XMp4   db    clk  vdd  vdd sky130_fd_pr__pfet_01v8 W=2 L=0.15
"""


def build_deck(states: np.ndarray, os_mV: float, theta: int) -> str:
    """One deck = fixed topology + per-trial `alter` loop over cell R values.

    Bit-lines blp0..blp{N} / bln0..bln{N} run cell 0 (far end) -> N (TIA);
    cell i taps segment node i. Drivers at +VR/2 (x_i = +1).
    """
    L = [f"* T3-5 replay column, N={N}, {states.shape[0]} trials",
         f".lib {LIB} tt",
         "Vdd vdd 0 1.8", "Vss vss 0 0", f"Vcm vcm 0 {VCM}",
         f"Vclk clk 0 PULSE(0 1.8 {T_SETTLE + T_CLK:.3g} 50p 50p 3n 20n)",
         f"Vdrv drv 0 dc {VCM + VR / 2.0:.6g}"]
    for i in range(N):
        L += [f"Rp{i} drv tp{i} {RP:.6g}",
              f"Rn{i} drv tn{i} {RP * (1 + TMR):.6g}",
              f"Rsegp{i} tp{i} blp{i} 1e-3",
              f"Rsegn{i} tn{i} bln{i} 1e-3"]
    # bit-line ladders (cell 0 far end), tap caps, TIA at the near end
    for i in range(N - 1):
        L += [f"Rblp{i} blp{i} blp{i + 1} {R_SEG:.6g}",
              f"Rbln{i} bln{i} bln{i + 1} {R_SEG:.6g}",
              f"Cblp{i} blp{i} 0 {C_TAP:.3g}",
              f"Cbln{i} bln{i} 0 {C_TAP:.3g}"]
    L += [f"Rblp_end blp{N - 1} vgp 1e-3",
          f"Rbln_end bln{N - 1} vgn 1e-3",
          # virtual-ground TIA: behavioral op-amp holds vgp/vgn at VCM,
          # feedback R_TI develops the popcount voltage at np/nn
          f"Eopp np 0 value={{{VCM} + 2e4*({VCM} - v(vgp))}}",
          f"Eopn nn 0 value={{{VCM} + 2e4*({VCM} - v(vgn))}}",
          f"RTIp np vgp {R_TI:.6g}",
          f"RTIn nn vgn {R_TI:.6g}",
          # common-mode cancellation (matched reference column): without it
          # the ~0.4 mA/side column current flows through R_TI and drags
          # the TIA outputs to -0.09 V, cutting the SA input pair off
          f"Icmp vgp 0 dc {N * (GP + GAP) / 2.0 * (VR / 2.0):.6g}",
          f"Icmn vgn 0 dc {N * (GP + GAP) / 2.0 * (VR / 2.0):.6g}",
          # BN threshold: differential reference current at (theta+1)*LSB
          f"Ithp vgp 0 dc {(theta + 1) * LSB_I / 2.0:.6g}",
          f"Ithn 0 vgn dc {(theta + 1) * LSB_I / 2.0:.6g}",
          sa_core(os_mV)]
    ctrl = [".control", "set noaskquit"]
    for t, s in enumerate(states):
        for i in range(N):
            rplus = RP if s[i] > 0 else RP * (1 + TMR)
            rminus = RP * (1 + TMR) if s[i] > 0 else RP
            ctrl += [f"alter Rp{i} {rplus:.6g}", f"alter Rn{i} {rminus:.6g}"]
        ctrl += [f"tran 50p {T_SETTLE + T_CLK + 4e-9:.3g}",
                 # pre-clock analog popcount + far-end IR + SA decision
                 "let vd = v(np)-v(nn)",
                 "let vf = v(blp0)-v(vgp)",
                 "let vo = v(outp)-v(outn)",
                 f"meas tran vpre FIND vd AT={T_SETTLE:.3g}",
                 f"meas tran vfar FIND vf AT={T_SETTLE:.3g}",
                 f"meas tran vout FIND vo AT={T_SETTLE + T_CLK + 3e-9:.3g}",
                 f"echo TRIAL {t} done", "destroy all"]
    ctrl += ["quit", ".endc", ".end"]
    return "\n".join(L + ctrl) + "\n"


def parse_out(text: str, n_trials: int):
    vpre = [float(x) for x in re.findall(
        r"vpre\s*=\s*([-+0-9.eE]+)", text)]
    vfar = [float(x) for x in re.findall(
        r"vfar\s*=\s*([-+0-9.eE]+)", text)]
    vout = [float(x) for x in re.findall(
        r"vout\s*=\s*([-+0-9.eE]+)", text)]
    if not (len(vpre) == len(vfar) == len(vout) == n_trials):
        raise RuntimeError(
            f"parse mismatch: {len(vpre)}/{len(vfar)}/{len(vout)} of "
            f"{n_trials}\n{text[-2000:]}")
    return np.array(vpre), np.array(vfar), np.array(vout)


def clopper_pearson_ub(k: int, n: int, conf: float) -> float:
    """Exact binomial upper confidence bound (no scipy: lgamma + bisection)."""
    from math import lgamma, log, exp
    if k >= n:
        return 1.0

    def binom_cdf(p: float) -> float:
        if p <= 0.0:
            return 1.0
        if p >= 1.0:
            return 0.0
        tot = 0.0
        for i in range(k + 1):
            tot += exp(lgamma(n + 1) - lgamma(i + 1) - lgamma(n - i + 1)
                       + i * log(p) + (n - i) * log(1.0 - p))
        return tot

    lo, hi = k / n if n else 0.0, 1.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if binom_cdf(mid) > 1.0 - conf:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _ks_stat(x: np.ndarray) -> float:
    from math import erf, sqrt
    n = len(x)
    mu, sd = float(x.mean()), float(x.std() or 1e-12)
    xs = np.sort(x)
    cdf = np.array([0.5 * (1.0 + erf((v - mu) / (sd * sqrt(2.0))))
                    for v in xs])
    return float(np.max(np.maximum(np.arange(1, n + 1) / n - cdf,
                                   cdf - np.arange(0, n) / n)))


def ks_norm(x: np.ndarray, n_mc: int = 2000, seed: int = 99):
    """LILLIEFORS normality check about the fitted mean/sd.

    Parameters are estimated from the sample, so the fully-specified
    Kolmogorov p-value would be ~5x anti-conservative; the null
    distribution of D is Monte-Carlo'd with re-fitted normals instead.
    """
    d = _ks_stat(x)
    rng = np.random.default_rng(seed)
    n = len(x)
    exceed = sum(_ks_stat(rng.standard_normal(n)) >= d
                 for _ in range(n_mc))
    return d, (exceed + 1) / (n_mc + 1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    rng = np.random.default_rng(SEED)
    # per-cell Bernoulli probabilities: mixed easy/hard column, fixed for
    # the whole experiment (one programmed column instance)
    p = np.clip(rng.uniform(0.1, 0.9, N), 0.0, 1.0)
    mu_pc = float(np.sum(2 * p - 1))
    sd_pc = float(np.sqrt(np.sum(4 * p * (1 - p))))
    theta = 2 * int(round(mu_pc / 2.0))      # even -> theta+1 odd, no ties
    print(f"column: R_TI={R_TI:.0f} ohm, LSB_I={LSB_I * 1e6:.3f} uA, "
          f"R_seg={R_SEG:.2f} ohm, E[pc]={mu_pc:.1f}, sd={sd_pc:.1f}, "
          f"theta+1={theta + 1}", flush=True)

    n_decks = 1 if args.smoke else N_DECKS
    n_tr = 5 if args.smoke else TRIALS_PER_DECK
    variants = {"os0": 0.0} if args.smoke else {"os0": 0.0, "os9": 9.21}

    results = {}
    for tag, os_mV in variants.items():
        agree, rows = 0, []
        all_pre, all_far, all_vout, all_states = [], [], [], []
        for d in range(n_decks):
            states = np.where(
                rng.random((n_tr, N)) < p[None, :], 1, -1)
            RUN.write_text(build_deck(states, os_mV, theta), encoding="ascii")
            out = subprocess.run(
                ["ngspice", "-b", RUN.name], cwd=HERE,
                capture_output=True, text=True, timeout=3600)
            vpre, vfar, vout = parse_out(out.stdout, n_tr)
            pc = states.sum(axis=1)
            beh = np.sign(pc - (theta + 1))
            cir = np.sign(vout)
            # analytic sign convention: vd = -R_TI * LSB_I * (pc-(theta+1))
            # (op output = VCM + gain*(VCM - v(vg)); signal current INTO the
            # virtual ground drives the output BELOW VCM)
            pol = -1.0
            agree += int(np.sum(pol * cir == beh))
            all_pre.append(pol * vpre)
            all_far.append(vfar)
            all_vout.append(vout)
            all_states.append(states)
            print(f"[{tag}] deck {d + 1}/{n_decks}: "
                  f"{int(np.sum(pol * cir == beh))}/{n_tr} agree", flush=True)
        n_tot = n_decks * n_tr
        vpre = np.concatenate(all_pre)
        vfar = np.concatenate(all_far)
        vout_all = np.concatenate(all_vout)
        pc = np.concatenate([s.sum(axis=1) for s in all_states])
        # analog popcount estimate and residual (in popcount units)
        pc_analog = vpre / (LSB_I * R_TI) + (theta + 1)
        resid = pc_analog - pc
        beh_all = np.sign(pc - (theta + 1))
        pol = -1.0
        # layer 1: SA faithfulness -- transistor SA resolves the analog sign
        sa_faith = float(np.mean(np.sign(pol * vout_all) == np.sign(vpre)))
        vout_mag = float(np.median(np.abs(vout_all)))
        # layer 3: one-point threshold recalibration (deck 0 calibrates,
        # decks 1+ evaluate), mirroring the C1 calibratable-offset flow
        n0 = n_tr
        bias_pc = float(resid[:n0].mean())
        if n_decks > 1:
            cal_dec = np.sign(pc_analog[n0:] - bias_pc - (theta + 1))
            agree_cal = int(np.sum(cal_dec == beh_all[n0:]))
            n_cal = n_tot - n0
        else:
            agree_cal, n_cal = 0, 0
        # slope compression fit: pc_analog = slope*pc + intercept
        A = np.vstack([pc, np.ones_like(pc)]).T
        slope, intercept = np.linalg.lstsq(A, pc_analog, rcond=None)[0]
        # exact binomial 95% upper bound on the disagreement rate
        n_dis = n_tot - agree
        ub = clopper_pearson_ub(n_dis, n_tot, 0.95)
        ks = ks_norm(resid)
        np.savez(HERE / f"_replay_trials_{tag}.npz",
                 pc=pc, pc_analog=pc_analog, vpre=vpre, vfar=vfar,
                 vout=vout_all)
        results[tag] = dict(
            n_trials=n_tot, n_agree=int(agree), n_disagree=int(n_dis),
            disagree_rate_ub95=ub,
            sa_faithfulness=sa_faith,
            recal_bias_pc=bias_pc,
            n_agree_recal=agree_cal, n_recal_eval=n_cal,
            disagree_rate_recal_ub95=(clopper_pearson_ub(
                n_cal - agree_cal, n_cal, 0.95) if n_cal else None),
            slope_fit=float(slope), intercept_fit=float(intercept),
            vout_median_V=vout_mag,
            resid_pc_mean=float(resid.mean()), resid_pc_std=float(resid.std()),
            resid_pc_max=float(np.abs(resid).max()),
            ks_stat=float(ks[0]), ks_p=float(ks[1]),
            ir_far_end_mV_mean=float(vfar.mean() * 1e3),
            ir_far_end_mV_max=float(np.abs(vfar).max() * 1e3),
            near_threshold_trials=int(np.sum(np.abs(pc - (theta + 1)) <= 3)),
        )
        print(f"[{tag}] agree {agree}/{n_tot} (UB95 {ub:.4f}); "
              f"SA-faith {sa_faith:.4f}; recal agree {agree_cal}/{n_cal}; "
              f"resid {resid.mean():+.3f}+-{resid.std():.3f} pc "
              f"(slope {slope:.4f}); far-end IR {vfar.mean() * 1e3:.2f} mV",
              flush=True)

    out = dict(N=N, R_TI_ohm=R_TI, LSB_I_uA=LSB_I * 1e6, R_seg_ohm=R_SEG,
               C_tap_fF=C_TAP * 1e15, theta_plus_1=theta + 1, seed=SEED,
               p_summary=dict(mu_pc=mu_pc, sd_pc=sd_pc),
               variants=results,
               power_note="a true disagreement rate of 0.32% (0.38%) "
                          "gives >=80% probability of at least one observed "
                          "disagreement in the n=500 (n=600) sample",
               scope="deterministic replay validates the readout-chain "
                     "joint effect (BL IR, TIA mapping, SA offset/"
                     "regeneration, settling); weight-bit stochasticity "
                     "lives in the harness RNG by architecture. Results "
                     "are conditional on one drawn column instance with "
                     "theta at E[pc] (deliberate near-threshold stress); "
                     "variants use independent state draws; recalibrated "
                     "agreement is an output-node projection of the "
                     "threshold shift")
    (HERE / "replay_column_cosim_summary.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")
    print("wrote replay_column_cosim_summary.json")


if __name__ == "__main__":
    main()
