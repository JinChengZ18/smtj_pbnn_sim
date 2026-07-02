#!/usr/bin/env python3
"""Faithful reproduction of Truong's parasitic-resistance-adapted programming scheme
(S. N. Truong, "A Parasitic Resistance-Adapted Programming Scheme for Memristor
Crossbar-Based Neuromorphic Computing Systems," Materials 12(24):4097, 2019,
DOI 10.3390/ma12244097, open access; PMC6947318), run on OUR committed sMTJ write-path model.

WHY THIS SCRIPT EXISTS
----------------------
The D.5 capability matrix carries a qualitative "parasitic-adapted programming" lineage; we want a
quantitative residual-write-error / P_sw-flatness point measured on OUR committed write-path model,
comparable in the same table to our per-row IR-aware pre-distortion (eda/hero/ir_aware_writedac.py).
INTEGRITY is the overriding constraint: (a) Truong's published equations are implemented verbatim
(quoted below), (b) the implementation is self-checked on HIS geometry (his Eq. (6) compensation is
an exact algebraic identity there), (c) the mapped scheme is evaluated ONLY on our committed model
constants and our committed measured DAC transfer, and (d) every adaptation his multi-level analog
method needed for our binary-P_sw write is documented. All numbers in the JSON are computed here.

TRUONG'S METHOD (verbatim equations, PMC6947318)
------------------------------------------------
Equivalent wire resistance by superposition. For the first row (his Eq. (4)):
    "R_1,i = ir + mr"
and in general ("In general, we can approximate the wire resistance for the cell M_j,i as
follows", his Eq. (5)):
    "R_j,i = ir + (m-j+1)r    where, m is the number of rows"
with r the single wire-segment resistance, i the column index (i segments along the input row
wire), and (m-j+1) the segment count down the output column wire to the sensing end. Derivation
sentence: "the resistors, which the current i1 passes through, can be approximately represented
by an equivalent resistor R_1,i".

Parasitic-resistance-adapted programming (his Eq. (6)):
    "M'_j,i = M_j,i - R_j,i"
i.e. the target memristance matrix is obtained by subtracting the equivalent-wire-resistance
matrix from the original connection matrix before the crossbar is programmed, so that in
operation the in-circuit series total M'_j,i + R_j,i equals the intended M_j,i.

Paper-reported results (their abstract, quoted; NOT our numbers): "The recognition rate of the
memristor crossbar with the conventional programming scheme is 99%, 95%, 81%, and 65% when wire
resistance is set to be 1.5, 2.0, 2.5, and 3.0 Ohm, respectively." / "the memristor crossbar with
the proposed parasitic resistance-adapted programming scheme can maintain the recognition as high
as 100% when wire resistance is as high as 3.0 Ohm." / wire-model accuracy "as low as 2.9%".

OUR COMMITTED MODEL (read at runtime where possible)
----------------------------------------------------
Device P_sw sigmoid P_sw(V) = 1/(1+exp(-(V-Vth)/V_T)), Vth = 0.895783 V, V_T = 23.414 mV; write
load R_dev = 776 ohm; calibrated write current I_write = 0.9/776 A (eda/hero/ir_aware_writedac.py;
operating point in eda/extraction/writeline/ir_drop_summary.json). Column: N = 256 rows, met2
write line, sheet R 0.125 ohm/sq (Magic-extracted), pitch 2 um, width 1 um -> per-segment
per-line resistance r_seg = 0.125*2/1 = 0.25 ohm; committed round-trip parasitic
R_par(row) = 2*r_seg*row (bit line out + source line back, both head-end). Fine write sub-DAC:
committed measured 6-bit resistor-string transfer (eda/hero/write_dac_resistor_string.json,
LSB 3.0411 mV, range 191.589 mV) -- the compensation rides this real measured transfer.

MAPPING (every adaptation documented; see "mapping_adaptations" in the JSON)
----------------------------------------------------------------------------
1. PREDICTION: Truong's superposition rule (sum the wire segments on the actual write-current
   path) instantiated on OUR committed one-hot column-write topology (head-end drive, head-end
   return) gives R(row) = row*r_seg + row*r_seg = 2*r_seg*row -- exactly our committed R_par(row),
   with r_seg from OUR extraction (not his 0.5-3 ohm examples). His literal (m-j+1) return count
   models HIS far-end-sensed column; keeping it would compensate a circuit we do not have.
2. PRE-DISTORTION: his Eq. (6) subtracts the predicted parasitic from the programmed MEMRISTANCE.
   Our sMTJ write is a binary stochastic event (fixed R_dev; nothing resistance-programmable), so
   the compensation must move to the write-VOLTAGE domain. The exact voltage-domain image of
   "make the in-circuit series operating point equal the target" under his own series-circuit
   algebra is V_head(row) = V_target*(R_dev+R_par(row))/R_dev = V_target + (V_target/R_dev)*R_par.
   Note the structural difference this preserves from the paper: Truong's correction is
   PROPORTIONAL TO THE TARGET (resistance-domain subtraction), while OUR committed scheme adds a
   FIXED-CALIBRATED-CURRENT drop, V_head(row) = V_target + I_write*R_par(row) with I_write=0.9/776.
3. DAC: both schemes' compensation increments are quantized onto the SAME committed measured
   resistor-string transfer (nearest measured increment v(code)-v(0)), so both ride the real DAC.
4. DELIVERY MODEL (ground truth for V_delivered): primary = the committed linearized model of
   ir_aware_writedac.py, V_del = V_head - I_write*R_par(row) (the model our benchmark numbers come
   from). Secondary = the exact series divider V_del = V_head*R_dev/(R_dev+R_par(row)), which for a
   one-hot write is the exact network solution (single conducting path -> series; no SPICE needed)
   and is the circuit algebra Truong's Eq. (6) presumes. Both are reported because near the far row
   the two compensation rules differ by (V_target/R_dev - I_write)*R_par -- each rule is exact
   under its own model, and hiding that would bias the comparison.

OUTPUT: truong_predistort_summary.json (next to this file). Numbers are only what this code
computes; nothing is typed by hand.

Run:  python eda/design_survey/repro/truong_predistort.py
"""
from __future__ import annotations
import json
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
IR_JSON = REPO / "eda" / "extraction" / "writeline" / "ir_drop_summary.json"
DAC_JSON = REPO / "eda" / "hero" / "write_dac_resistor_string.json"
BENCH_JSON = REPO / "eda" / "hero" / "ir_aware_writedac_summary.json"

# Committed device/write-path constants (eda/hero/ir_aware_writedac.py).
VTH, VT, RDEV = 0.895783, 0.023414, 776.0
I_WRITE = 0.9 / RDEV                       # calibrated write current (committed)
PITCH_UM, W_UM, LAYER = 2.0, 1.0, "met2"   # committed geometry (ir_aware_writedac.py)
N = 256
P_TARGETS = (0.5, 0.9, 0.99)


def psw(v):
    return 1.0 / (1.0 + math.exp(-(v - VTH) / VT))


def v_target(p):
    return VTH + VT * math.log(p / (1.0 - p))


# ---------------------------------------------------------------------------------------------
# Truong Eq. (5) family: superposition wire-resistance prediction.
# ---------------------------------------------------------------------------------------------
def truong_R(j, i, m, r):
    """Truong Eq. (5) verbatim on HIS geometry: R_j,i = i*r + (m-j+1)*r."""
    return i * r + (m - j + 1) * r


def truong_compensate(M, R):
    """Truong Eq. (6) verbatim: M'_j,i = M_j,i - R_j,i (element-wise)."""
    return [[M[j][i] - R[j][i] for i in range(len(M[0]))] for j in range(len(M))]


# ---------------------------------------------------------------------------------------------
# The same superposition rule instantiated on OUR committed one-hot column-write topology:
# bit line head -> row (row segments) + source line row -> head-end ground (row segments).
# ---------------------------------------------------------------------------------------------
def r_par(row, r_seg):
    return 2.0 * r_seg * row


# ---------------------------------------------------------------------------------------------
# Delivery models (ground truth for the voltage the cell sees given the head voltage).
# ---------------------------------------------------------------------------------------------
def deliver_committed_linear(v_head, rp):
    """Committed model (ir_aware_writedac.py): V_del = V_head - I_write*R_par, I_write fixed."""
    return v_head - I_WRITE * rp


def deliver_exact_divider(v_head, rp):
    """Exact one-hot network solution (single conducting path -> series divider)."""
    return v_head * RDEV / (RDEV + rp)


DELIVERY = {"committed_linear": deliver_committed_linear,
            "exact_divider": deliver_exact_divider}


# ---------------------------------------------------------------------------------------------
# Compensation rules (ideal head-voltage increment above V_target, before DAC quantization).
# ---------------------------------------------------------------------------------------------
def dv_nopd(rp, vt):
    return 0.0


def dv_ours(rp, vt):
    """OUR committed rule (ir_aware_writedac.py): fixed calibrated current, dV = I_write*R_par."""
    return I_WRITE * rp


def dv_truong(rp, vt):
    """Truong Eq. (6) mapped to the voltage domain: proportional-to-target, dV=(V_t/R_dev)*R_par."""
    return (vt / RDEV) * rp


SCHEMES = {"nopd": dv_nopd, "ours_ir_aware": dv_ours, "truong_adapted": dv_truong}


def main():
    # ------------------------- committed inputs, with provenance gates -------------------------
    ir = json.loads(IR_JSON.read_text(encoding="utf-8"))
    dac = json.loads(DAC_JSON.read_text(encoding="utf-8"))
    bench = json.loads(BENCH_JSON.read_text(encoding="utf-8"))

    rs_met2 = ir["sheet_R_TT"][LAYER]
    r_seg = rs_met2 * PITCH_UM / W_UM                      # per-segment per-line [ohm]
    assert abs(ir["operating_point"]["I_write_mA"] - I_WRITE * 1e3) < 1e-9, \
        "committed operating-point current mismatch"
    assert abs(r_par(N, r_seg) - 128.0) < 1e-9, "R_par(256) != committed 128 ohm"
    assert abs(I_WRITE * r_par(N, r_seg) * 1e3 - ir["realistic_met2_W1_pitch2"][2]["IR_mV"]) < 1e-6, \
        "max IR drop != committed extraction value"

    # Committed measured DAC transfer -> increments relative to code 0 (the fine sub-DAC codes).
    codes = [e["code"] for e in dac["transfer"]]
    vload = [e["v_load"] for e in dac["transfer"]]
    assert codes == list(range(64)), "unexpected DAC transfer"
    dinc = [v - vload[0] for v in vload]                   # measured increment per code [V]
    lsb = (vload[-1] - vload[0]) / 63.0
    assert abs(lsb * 1e3 - dac["LSB_mV"]) < 5e-4, "recomputed LSB != committed LSB_mV"

    def ride_dac(dv_ideal):
        """Static calibration: pick the code whose MEASURED increment best matches dv_ideal."""
        c = min(range(64), key=lambda k: abs(dinc[k] - dv_ideal))
        return c, dinc[c]

    # ------------------------- self-check 1: Truong's Eq. (5)/(6) on HIS geometry --------------
    m_t, n_t, r_t = 64, 26, 3.0                            # his 64-input, 26-column example, r=3 ohm
    rng = random.Random(0)
    M = [[rng.uniform(6e4, 2e5) for _ in range(n_t)] for _ in range(m_t)]
    R = [[truong_R(j, i, m_t, r_t) for i in range(1, n_t + 1)] for j in range(1, m_t + 1)]
    Mp = truong_compensate(M, R)
    ident_err = max(abs(Mp[j][i] + R[j][i] - M[j][i])
                    for j in range(m_t) for i in range(n_t))
    eq4_ok = all(abs(truong_R(1, i, m_t, r_t) - (i * r_t + m_t * r_t)) == 0.0
                 for i in range(1, n_t + 1))
    selfcheck_truong = dict(
        m=m_t, n=n_t, r_ohm=r_t,
        eq4_R1i_matches_ir_plus_mr=eq4_ok,
        eq6_identity_max_error_ohm=ident_err,
        R_range_ohm=[min(min(row) for row in R), max(max(row) for row in R)],
        note="Eq.(6) makes the in-circuit series total M'+R equal M exactly (algebraic identity); "
             "verifies the coded compensation is his subtraction, on his own m=64/n=26/r=3 example.")
    assert ident_err == 0.0 and eq4_ok

    # ------------------------- self-check 2: no-compensation spread == committed benchmark -----
    p_bench = bench["p_target"]                            # 0.9
    vt_bench = v_target(p_bench)
    p_nopd = [psw(vt_bench - I_WRITE * r_par(k, r_seg)) for k in range(N + 1)]
    spread_nopd = max(p_nopd) - min(p_nopd)
    assert abs(round(spread_nopd, 4) - bench["psw_spread_nopd"]) < 1e-9, \
        "no-compensation spread does not reproduce committed benchmark"

    # ------------------------- main evaluation ------------------------------------------------
    results = {}
    for p in P_TARGETS:
        vt = v_target(p)
        per_model = {}
        for mname, deliver in DELIVERY.items():
            per_scheme = {}
            for sname, dv_rule in SCHEMES.items():
                dvs, dvq, code_used, vdel, ps = [], [], [], [], []
                for k in range(N + 1):
                    rp = r_par(k, r_seg)
                    dv = dv_rule(rp, vt)
                    c, d = (0, 0.0) if sname == "nopd" else ride_dac(dv)
                    v = deliver(vt + d, rp)
                    dvs.append(dv)
                    dvq.append(d)
                    code_used.append(c)
                    vdel.append(v)
                    ps.append(psw(v))
                dv_err = [v - vt for v in vdel]
                # ideal (unquantized) rule error under this delivery model, to separate the
                # compensation-rule error from the DAC quantization error:
                dv_err_ideal = [deliver(vt + dvs[k], r_par(k, r_seg)) - vt for k in range(N + 1)]
                kmaxV = max(range(N + 1), key=lambda k: abs(dv_err[k]))
                kmaxP = max(range(N + 1), key=lambda k: abs(ps[k] - p))
                detail = [dict(row=k, R_par_ohm=round(r_par(k, r_seg), 1),
                               code=code_used[k], dv_applied_mV=round(dvq[k] * 1e3, 3),
                               v_del=round(vdel[k], 5), psw=round(ps[k], 4))
                          for k in range(0, N + 1, 32)]
                per_scheme[sname] = dict(
                    max_abs_dV_mV=round(max(abs(x) for x in dv_err) * 1e3, 3),
                    worst_row_dV=kmaxV,
                    max_abs_dV_mV_ideal_rule=round(max(abs(x) for x in dv_err_ideal) * 1e3, 3),
                    max_abs_dPsw=round(max(abs(x - p) for x in ps), 4),
                    worst_row_dPsw=kmaxP,
                    psw_min=round(min(ps), 4), psw_max=round(max(ps), 4),
                    psw_spread=round(max(ps) - min(ps), 4),
                    max_code=max(code_used),
                    rows=detail)
            per_model[mname] = per_scheme
        results[f"P{p}"] = dict(V_target=round(vt, 6), models=per_model)

    # ------------------------- console table --------------------------------------------------
    print("=" * 100)
    print("Truong parasitic-adapted programming -- faithful repro on our committed write path")
    print(f"N={N}, r_seg={r_seg} ohm ({LAYER}, extracted), R_par(256)={r_par(N, r_seg):.0f} ohm, "
          f"I_write={I_WRITE*1e3:.4f} mA, DAC LSB={lsb*1e3:.4f} mV (measured transfer)")
    print("=" * 100)
    for p in P_TARGETS:
        vt = v_target(p)
        print(f"\nP_target={p} (V_target={vt:.4f} V)")
        print(f"  {'scheme':<16}{'model':<18}{'max|dV| mV':>11}{'(rule-only)':>12}"
              f"{'max|dPsw|':>11}{'Psw spread':>12}{'max code':>10}")
        for mname in DELIVERY:
            for sname in SCHEMES:
                r = results[f"P{p}"]["models"][mname][sname]
                print(f"  {sname:<16}{mname:<18}{r['max_abs_dV_mV']:>11.3f}"
                      f"{r['max_abs_dV_mV_ideal_rule']:>12.3f}{r['max_abs_dPsw']:>11.4f}"
                      f"{r['psw_spread']:>12.4f}{r['max_code']:>10d}")

    # ------------------------- headline (D.2-comparable point, p=0.9, committed model) --------
    h = results["P0.9"]["models"]
    headline = dict(
        p_target=0.9,
        committed_linear=dict(
            nopd_max_abs_dV_mV=h["committed_linear"]["nopd"]["max_abs_dV_mV"],
            nopd_max_abs_dPsw=h["committed_linear"]["nopd"]["max_abs_dPsw"],
            ours_max_abs_dV_mV=h["committed_linear"]["ours_ir_aware"]["max_abs_dV_mV"],
            ours_max_abs_dPsw=h["committed_linear"]["ours_ir_aware"]["max_abs_dPsw"],
            truong_max_abs_dV_mV=h["committed_linear"]["truong_adapted"]["max_abs_dV_mV"],
            truong_max_abs_dPsw=h["committed_linear"]["truong_adapted"]["max_abs_dPsw"]),
        exact_divider=dict(
            nopd_max_abs_dV_mV=h["exact_divider"]["nopd"]["max_abs_dV_mV"],
            nopd_max_abs_dPsw=h["exact_divider"]["nopd"]["max_abs_dPsw"],
            ours_max_abs_dV_mV=h["exact_divider"]["ours_ir_aware"]["max_abs_dV_mV"],
            ours_max_abs_dPsw=h["exact_divider"]["ours_ir_aware"]["max_abs_dPsw"],
            truong_max_abs_dV_mV=h["exact_divider"]["truong_adapted"]["max_abs_dV_mV"],
            truong_max_abs_dPsw=h["exact_divider"]["truong_adapted"]["max_abs_dPsw"]))

    # rule difference between the two compensations (computed, not asserted):
    rule_diff_mV = {f"P{p}": round(abs(v_target(p) / RDEV - I_WRITE) * r_par(N, r_seg) * 1e3, 3)
                    for p in P_TARGETS}

    out = {
        "_about": "Faithful reproduction of Truong's parasitic-resistance-adapted programming "
                  "(Materials 12:4097, 2019) mapped onto our committed sMTJ write path. Numbers "
                  "are computed by this script only.",
        "_paper": "S. N. Truong, 'A Parasitic Resistance-Adapted Programming Scheme for Memristor "
                  "Crossbar-Based Neuromorphic Computing Systems,' Materials 12(24):4097, 2019, "
                  "DOI 10.3390/ma12244097 (open access; PMC6947318).",
        "_equations_implemented": [
            "Eq.(4) 'R_1,i = ir + mr' (first-row equivalent wire resistance, superposition)",
            "Eq.(5) 'R_j,i = ir + (m-j+1)r  where, m is the number of rows' (general cell)",
            "Eq.(6) 'M'_j,i = M_j,i - R_j,i' (target memristance matrix minus the equivalent "
            "wire-resistance matrix, applied before programming)"],
        "_paper_reported_results_quoted": [
            "conventional: 'recognition rate ... is 99%, 95%, 81%, and 65% when wire resistance "
            "is set to be 1.5, 2.0, 2.5, and 3.0 Ohm'",
            "proposed: 'can maintain the recognition as high as 100% when wire resistance is as "
            "high as 3.0 Ohm'",
            "wire-model accuracy: 'discrepancy of the output voltages ... as low as 2.9%'"],
        "selfchecks": dict(
            truong_eq5_eq6_on_his_geometry=selfcheck_truong,
            nopd_spread_reproduces_committed_benchmark=dict(
                computed=round(spread_nopd, 4), committed=bench["psw_spread_nopd"], match=True),
            dac_lsb_reproduces_committed=dict(
                computed_mV=round(lsb * 1e3, 4), committed_mV=dac["LSB_mV"], match=True),
            max_IR_matches_committed_extraction=dict(
                computed_mV=round(I_WRITE * r_par(N, r_seg) * 1e3, 4),
                committed_mV=round(ir["realistic_met2_W1_pitch2"][2]["IR_mV"], 4), match=True)),
        "our_model_provenance": dict(
            VTH=VTH, VT=VT, RDEV_ohm=RDEV, I_write_mA=round(I_WRITE * 1e3, 4),
            layer=LAYER, sheet_R_ohm_sq=rs_met2, pitch_um=PITCH_UM, W_um=W_UM,
            r_seg_ohm_per_line=r_seg, R_par_row256_ohm=r_par(N, r_seg),
            dac="committed measured 6-bit resistor-string transfer "
                "(eda/hero/write_dac_resistor_string.json)",
            dac_LSB_mV=dac["LSB_mV"], dac_range_mV=dac["range_mV"], dac_INL_LSB=dac["INL_LSB"]),
        "mapping_adaptations": [
            "PREDICTION KEPT, GEOMETRY OURS: Truong's superposition rule (sum the wire segments "
            "on the actual current path; his Eq. (5) family) instantiated on our committed one-hot "
            "column write (head-end drive + head-end return) gives R(row)=2*r_seg*row with "
            "r_seg=0.25 ohm from OUR extracted met2 sheet R -- identical to the committed "
            "R_par(row). His literal (m-j+1) return count belongs to his far-end-sensed column; "
            "applying it verbatim would compensate a circuit we do not have (a far-end-grounded "
            "return would instead make R(row)=N*r_seg, position-independent -- a different layout, "
            "not our committed one).",
            "DOMAIN ADAPTED (required): his Eq. (6) pre-distorts the programmed MEMRISTANCE; our "
            "sMTJ has a fixed 776-ohm write load and a binary stochastic state, so nothing "
            "resistance-programmable exists. The compensation is moved to the write-voltage "
            "domain: V_head(row) = V_target*(R_dev+R_par(row))/R_dev, the exact image of 'restore "
            "the in-circuit operating point' under his own series-circuit algebra. This preserves "
            "his structure: the correction is PROPORTIONAL TO THE TARGET, whereas our committed "
            "scheme adds a FIXED-calibrated-current drop I_write*R_par(row).",
            "GRANULARITY KEPT: like his connection-matrix update, the compensation is a static "
            "per-cell (here per-row) lookup computed once from nominal geometry; no write-verify "
            "feedback is added (the paper reports none).",
            "DAC: both schemes' increments ride the SAME committed measured resistor-string "
            "transfer (nearest measured increment v(code)-v(0)); Truong's compensation is analog-"
            "continuous in the paper, so quantization is our platform's constraint, applied "
            "identically to both.",
            "DELIVERY MODELS: primary ground truth is the committed linearized model "
            "V_del=V_head-I_write*R_par (ir_aware_writedac.py, the benchmark's model); the exact "
            "series divider V_del=V_head*R_dev/(R_dev+R_par) is reported alongside because a "
            "one-hot write is exactly a series circuit (which is also why no SPICE run is needed: "
            "there is a single conducting path, and the sneak-path complexity that motivates "
            "circuit simulation in Truong's inference crossbar is absent). Each compensation rule "
            "is exact under its own model; reporting only one would bias the comparison."],
        "results": results,
        "rule_difference_ours_vs_truong_at_row256_mV": rule_diff_mV,
        "headline_D2_point": headline,
        "assumptions": [
            "Committed device constants VTH=0.895783 V, V_T=23.414 mV, R_dev=776 ohm and the "
            "calibrated I_write=0.9/776 A are taken from eda/hero/ir_aware_writedac.py / "
            "eda/extraction/writeline/ir_drop_summary.json (asserted at runtime).",
            "Per-segment wire resistance r_seg=sheet_R*pitch/W=0.25 ohm per line per row (met2, "
            "pitch 2 um, W 1 um) -- our committed geometry, replacing Truong's uniform 0.5-3 ohm "
            "example values.",
            "The fine sub-DAC increment for code c is the measured v_load(c)-v_load(0) from the "
            "committed transfer (riding the real DAC including its INL of 0.48 LSB); the coarse "
            "write level is assumed to sit at V_target exactly (per-column trim is a separate, "
            "orthogonal mechanism).",
            "Rows are evaluated at k=0..256 inclusive, matching the committed benchmark's row "
            "range.",
            "The committed benchmark (ir_aware_writedac_summary.json) reports our scheme "
            "UNQUANTIZED (psw_pd=0.9 exactly); in the comparison table here BOTH schemes are "
            "quantized to the same measured DAC, so 'ours' carries its honest quantization "
            "residual too."],
    }

    # Conclusion assembled from computed numbers only.
    cl, ed = headline["committed_linear"], headline["exact_divider"]
    out["conclusion"] = (
        "Truong's method was implemented from his published equations (Eq. (4)/(5) superposition "
        "wire-resistance prediction, Eq. (6) subtract-the-parasitic pre-distortion) and verified "
        "as an exact identity on his own 64x26/r=3-ohm geometry. Mapped onto our committed one-hot "
        "column write, his prediction instantiates to exactly our extracted R_par(row)=0.5*row "
        "ohm, and his compensation -- adapted of necessity from the memristance domain to the "
        "write-voltage domain, because a binary sMTJ has no programmable resistance -- becomes a "
        "proportional-to-target head-voltage pre-distortion that differs from our fixed-current "
        f"rule by (V_target/R_dev - I_write)*R_par, i.e. by {rule_diff_mV['P0.5']}/"
        f"{rule_diff_mV['P0.9']}/{rule_diff_mV['P0.99']} mV at the far row for P_target="
        "0.5/0.9/0.99. On the committed linearized delivery model (the benchmark's), riding the "
        f"same measured 3.04 mV DAC: no compensation leaves max|dV|={cl['nopd_max_abs_dV_mV']} mV "
        f"and max|dPsw|={cl['nopd_max_abs_dPsw']} at P_target=0.9; our IR-aware rule leaves "
        f"{cl['ours_max_abs_dV_mV']} mV / {cl['ours_max_abs_dPsw']}; Truong-adapted leaves "
        f"{cl['truong_max_abs_dV_mV']} mV / {cl['truong_max_abs_dPsw']}. Under the exact series-"
        f"divider model the ranking mirrors (ours {ed['ours_max_abs_dV_mV']} mV / "
        f"{ed['ours_max_abs_dPsw']}, Truong-adapted {ed['truong_max_abs_dV_mV']} mV / "
        f"{ed['truong_max_abs_dPsw']}), because each rule is exact under its own circuit model. "
        "FAITHFUL OUTCOME: Truong's parasitic-adapted programming transfers cleanly to our write "
        "path and flattens P_sw to within a few times the DAC quantization floor, essentially "
        "matching our scheme; the two schemes' residuals differ only through the compensation "
        "current (target-proportional vs fixed-calibrated) at the few-mV / few-LSB level, and "
        "which one is exactly zero-residual (pre-quantization) depends on the delivery model. "
        "The honest D.2 entry is therefore parity-at-the-quantization-floor, not a win for either "
        "scheme; the uncompensated column remains the catastrophic case.")

    (HERE / "truong_predistort_summary.json").write_text(json.dumps(out, indent=2))
    print("\n" + "=" * 100)
    print(out["conclusion"])
    print("=" * 100)
    print("wrote truong_predistort_summary.json")


if __name__ == "__main__":
    main()
