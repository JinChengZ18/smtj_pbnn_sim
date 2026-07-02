#!/usr/bin/env python3
"""Open-record-faithful reproduction of Zhu et al.'s line-resistance compensation, run on OUR
committed sMTJ write-path model, for the D.3 residual-write-error comparison.

PAPER
-----
Xi Zhu, Zhiwei Li, Haijun Liu, Qingjiang Li, Sen Liu, Nan Li, Hui Xu, "Solution to alleviate the
impact of line resistance on the crossbar array," IET Circuits, Devices & Systems 14(4):498-504,
2020, DOI 10.1049/iet-cds.2019.0313. The full text is PAYWALLED (Wiley/IET both returned
HTTP 402/403 at reproduction time), so this reproduction is built ONLY from the open record:

Open record item 1 -- the abstract (Crossref metadata for DOI 10.1049/iet-cds.2019.0313), verbatim:
  "However, the voltage drop caused by the current flowing through the access lines could be
   aggressive for the resistive crossbar array in a fully parallel fashion. In this study, the
   authors analysed the impact of the line resistance on the crossbar array based on the SPICE
   simulation. It implies that the scale of the crossbar array and the ratio of line resistance
   to resistive random access memory resistance bring great influence on the performance of the
   crossbar array. Also an scheme of optimisation has been proposed to diminish its influence."

Open record item 2 -- the only substantive citation context found (Semantic Scholar citation
contexts for the DOI; from Qin et al., "Design of High Robustness BNN Inference Accelerator Based
on Binary Memristors," 2020, same NUDT group), verbatim:
  "Zhu et al. [35] linearly mapped the distorted current from the range of current of the extreme
   array with wire resistance to the range of current of the extreme array without wire
   resistance."

WHAT THE OPEN RECORD SUPPORTS (and what it does not)
----------------------------------------------------
Supported: (a) a SPICE line-resistance IR-drop analysis, and (b) a compensation that is a GLOBAL
LINEAR RECALIBRATION anchored at the array EXTREMES -- mapping the distorted range back onto the
ideal (no-wire-resistance) range. NOT confirmable from the open record: per-position (per-row)
granularity, or the exact node where the linear map is applied (input drive vs. output current).

GRANULARITY ASSUMPTION (honest, as the task requires): we implement the defensible reading -- a
GLOBAL write-voltage boost, identical for every row, calibrated from the line-IR analysis. On a
write path with one shared driver operated at a single write point, ANY global linear map
degenerates to a single voltage offset at that operating point, so the scheme family is fully
characterized by one boost value dV. We evaluate: (i) dV calibrated to the EXTREME (worst-case)
row -- the reading closest to the citation context's "extreme array" anchoring; (ii) dV calibrated
to the MID row (minimizes the worst-case |voltage error|); and (iii) a full sweep of every DAC
code, whose optimum upper-bounds EVERYTHING any global calibration of this family could achieve.
We do NOT implement a per-row variant under Zhu's name: that granularity is not in the open
record (and would simply coincide with our own design).

CONTEXT TRANSPLANT (marked honestly): Zhu's setting is an RRAM crossbar doing weighted-sum
readout; ours is a write path. What we transplant is the compensation PRINCIPLE the open record
establishes -- a calibrated global correction for access-line IR loss anchored at the array
extreme -- applied to the one node our write path exposes, the shared drive voltage.

OUR MODEL (identical to the committed benchmark, eda/hero/ir_aware_writedac.py)
-------------------------------------------------------------------------------
N=256 column; round-trip parasitic R_par(r) = 2*Rs*(r*pitch/W) with the Magic-extracted sky130
met2 Rs=0.125 ohm/sq, pitch=2 um, W=1 um; write load 776 ohm; calibrated write current
I_wr = 0.9 V / 776 ohm = 1.16 mA (fixed-current linearization inherited from the committed
benchmark: IR(r) = I_wr*R_par(r) independent of the boost); device P_sw sigmoid with
V_th=0.895783 V, V_T=23.414 mV; write target p=0.90 -> V_target = V_th + V_T*ln(9). All
compensation voltages (Zhu's global boost AND our per-row pre-distortion) are quantized to the
MEASURED resistor-string write-DAC LSB (eda/hero/write_dac_resistor_string.json, 3.0411 mV,
6-bit). Every number in the output JSON is computed here; the no-compensation case is
self-checked against the committed ir_aware_writedac_summary.json row by row.

Run: python eda/design_survey/repro/zhu_boost.py   (pure Python, deterministic, no RNG)
"""
from __future__ import annotations
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
HERO = REPO / "eda" / "hero"

# ---- committed model constants (same source as eda/hero/ir_aware_writedac.py) -----------------
VTH, VT, RSOT = 0.895783, 0.023414, 776.0
I_WRITE = 0.9 / RSOT                      # 1.16 mA, fixed-current linearization (committed)
RS_MET2 = 0.125                           # ohm/sq, Magic-extracted (committed)
PITCH_UM, W_UM = 2.0, 1.0
N = 256
P_TARGET = 0.90
V_TARGET = VTH + VT * math.log(P_TARGET / (1 - P_TARGET))

# ---- measured write-DAC LSB (read from the committed sim result, not assumed) ------------------
DAC = json.loads((HERO / "write_dac_resistor_string.json").read_text(encoding="utf-8"))
LSB = DAC["LSB_mV"] * 1e-3                # 3.0411 mV measured into the 776 ohm load
NCODES = 2 ** DAC["nbits"]                # 6-bit -> codes 0..63


def r_par(r):
    return 2.0 * RS_MET2 * (r * PITCH_UM / W_UM)


def ir(r):
    return I_WRITE * r_par(r)


def psw(v):
    return 1.0 / (1.0 + math.exp(-(v - VTH) / VT))


def quant(v):
    """Quantize a compensation voltage to the measured DAC LSB (nearest code, clamped)."""
    code = int(math.floor(v / LSB + 0.5))
    code = max(0, min(NCODES - 1, code))
    return code, code * LSB


ROWS = list(range(0, N + 1))              # r = 0..N inclusive, exactly as the committed benchmark
SAMPLE = list(range(0, N + 1, N // 8))


def evaluate(boost_of_r, name, granularity, calibration):
    """Metrics for a scheme given boost(r) [V, already quantized]. All rows r=0..N."""
    p = [psw(V_TARGET + boost_of_r(r) - ir(r)) for r in ROWS]
    err = [abs(x - P_TARGET) for x in p]
    verr = [abs(boost_of_r(r) - ir(r)) for r in ROWS]
    boosts = [boost_of_r(r) for r in ROWS]
    rms = math.sqrt(sum(e * e for e in err) / len(err))
    return dict(
        scheme=name, granularity=granularity, calibration=calibration,
        rms_p_err=round(rms, 4),
        max_abs_p_err=round(max(err), 4),
        mean_abs_p_err=round(sum(err) / len(err), 4),
        psw_min=round(min(p), 4), psw_max=round(max(p), 4),
        psw_spread=round(max(p) - min(p), 4),
        max_v_err_mV=round(max(verr) * 1e3, 2),
        max_v_err_over_VT=round(max(verr) / VT, 2),
        mean_boost_mV=round(sum(boosts) / len(boosts) * 1e3, 2),
        max_boost_mV=round(max(boosts) * 1e3, 2),
        rows=[dict(row=r, boost_mV=round(boost_of_r(r) * 1e3, 2),
                   v_cell=round(V_TARGET + boost_of_r(r) - ir(r), 4),
                   psw=round(psw(V_TARGET + boost_of_r(r) - ir(r)), 4)) for r in SAMPLE])


def main():
    # ---- self-check: the no-comp case must reproduce the committed benchmark row by row -------
    committed = json.loads((HERO / "ir_aware_writedac_summary.json").read_text(encoding="utf-8"))
    assert round(V_TARGET, 4) == committed["V_target"], "V_target mismatch vs committed"
    p_nopd = [psw(V_TARGET - ir(r)) for r in ROWS]
    spread = max(p_nopd) - min(p_nopd)
    assert round(spread, 4) == committed["psw_spread_nopd"], "no-comp spread mismatch vs committed"
    for row in committed["rows"]:
        assert round(psw(V_TARGET - ir(row["row"])), 4) == row["psw_nopd"], \
            f"row {row['row']} psw mismatch vs committed"
    selfcheck = dict(
        V_target_matches_committed=True,
        nopd_spread_matches_committed=round(spread, 4) == committed["psw_spread_nopd"],
        nopd_rows_match_committed=True,
        committed_file="eda/hero/ir_aware_writedac_summary.json",
        psw_spread_nopd_committed=committed["psw_spread_nopd"],
        psw_spread_nopd_recomputed=round(spread, 4))

    # ---- schemes -------------------------------------------------------------------------------
    schemes = []

    # (0) no compensation: shared driver at V_target (the committed baseline).
    schemes.append(evaluate(lambda r: 0.0, "no_comp", "none", "none"))

    # (1) Zhu global boost, EXTREME-row calibration (closest to the citation context's
    #     "extreme array" anchoring): dV = IR(N), one DAC code for the whole column.
    code_w, dv_w = quant(ir(N))
    s = evaluate(lambda r: dv_w, "zhu_boost_global_worst", "global (one code, all rows)",
                 f"extreme row r=N={N}: dV=IR(N)={ir(N)*1e3:.2f} mV -> code {code_w} "
                 f"({dv_w*1e3:.2f} mV)")
    s["dac_code"] = code_w
    schemes.append(s)

    # (2) Zhu global boost, MID-row calibration (minimizes worst-case |voltage error|):
    #     dV = IR(N/2).
    code_m, dv_m = quant(ir(N // 2))
    s = evaluate(lambda r: dv_m, "zhu_boost_global_mid", "global (one code, all rows)",
                 f"mid row r={N//2}: dV=IR(N/2)={ir(N//2)*1e3:.2f} mV -> code {code_m} "
                 f"({dv_m*1e3:.2f} mV)")
    s["dac_code"] = code_m
    schemes.append(s)

    # (3) Sweep EVERY DAC code: the optimum upper-bounds any global calibration of the family.
    sweep = []
    for c in range(NCODES):
        dv = c * LSB
        p = [psw(V_TARGET + dv - ir(r)) for r in ROWS]
        e = [abs(x - P_TARGET) for x in p]
        sweep.append(dict(code=c, boost_mV=round(dv * 1e3, 2),
                          rms_p_err=round(math.sqrt(sum(x * x for x in e) / len(e)), 4),
                          max_abs_p_err=round(max(e), 4)))
    best = min(sweep, key=lambda d: d["rms_p_err"])
    dv_b = best["code"] * LSB
    s = evaluate(lambda r: dv_b, "zhu_boost_global_bestRMS", "global (one code, all rows)",
                 f"swept all {NCODES} codes, min RMS p-error at code {best['code']} "
                 f"({dv_b*1e3:.2f} mV) -- upper bound of ANY global calibration")
    s["dac_code"] = best["code"]
    schemes.append(s)

    # (4) OUR committed design: per-row IR pre-distortion, quantized to the same DAC LSB.
    def ours(r):
        return quant(ir(r))[1]
    s = evaluate(ours, "ours_perrow_predistortion", "per-row (one code per row)",
                 f"code(r)=round(IR(r)/LSB), r=0..{N}; codes 0..{quant(ir(N))[0]}")
    s["dac_code_range"] = [0, quant(ir(N))[0]]
    schemes.append(s)

    # (5) OUR design unquantized (== the committed ir_aware_writedac.py ideal case, tie-back).
    schemes.append(evaluate(ir, "ours_perrow_ideal_unquantized", "per-row (continuous)",
                            "dV(r)=IR(r) exactly (committed ideal; no DAC quantization)"))

    by = {s["scheme"]: s for s in schemes}
    comparison_table = [
        dict(scheme="no compensation", is_ours=False,
             **{k: by["no_comp"][k] for k in
                ("rms_p_err", "max_abs_p_err", "psw_spread", "psw_min",
                 "mean_boost_mV", "max_boost_mV")}),
        dict(scheme="Zhu global voltage boost (extreme-row calibrated)", is_ours=False,
             **{k: by["zhu_boost_global_worst"][k] for k in
                ("rms_p_err", "max_abs_p_err", "psw_spread", "psw_min",
                 "mean_boost_mV", "max_boost_mV")}),
        dict(scheme="ours: per-row IR pre-distortion (DAC-quantized)", is_ours=True,
             **{k: by["ours_perrow_predistortion"][k] for k in
                ("rms_p_err", "max_abs_p_err", "psw_spread", "psw_min",
                 "mean_boost_mV", "max_boost_mV")}),
    ]

    concl = (
        "A global write-voltage boost (the defensible open-record reading of Zhu's scheme) cannot "
        "flatten a position error that spans %.1f V_T: the sigmoid P_sw punishes any residual. "
        "Extreme-row calibration (code %d, %.2f mV on every row) restores the far row exactly but "
        "overdrives every nearer row into saturation -- P_sw spread collapses from %.4f to %.4f, "
        "but the residual write error floors at RMS %.4f (max %.4f) because rows near the driver "
        "sit at P_sw~%.4f instead of the 0.90 target. Mid-row calibration is far worse (RMS %.4f: "
        "the sigmoid saturates benignly on overdrive but collapses on underdrive, so the far half "
        "of the column fails). The full DAC-code sweep confirms code %d is the best ANY global "
        "calibration can do (RMS %.4f) -- for a deterministic write, overdrive would be harmless "
        "and Zhu's extreme-anchored global boost would suffice; for OUR p-bit array, where P_sw "
        "IS the signal, overshoot is as much an error as undershoot. Our per-row pre-distortion, "
        "quantized to the SAME measured 3.04 mV DAC LSB, keeps every row within half an LSB of "
        "target: RMS residual %.4f (max %.4f), %sx below the best global boost, at HALF the mean "
        "added drive (%.1f vs %.1f mV/row). The residual-write-error D.3 point is therefore: "
        "no-comp %.4f / Zhu global boost %.4f / ours %.4f (RMS |P_sw - 0.90| over %d rows)."
        % (ir(N) / VT, code_w, dv_w * 1e3,
           by["no_comp"]["psw_spread"], by["zhu_boost_global_worst"]["psw_spread"],
           by["zhu_boost_global_worst"]["rms_p_err"], by["zhu_boost_global_worst"]["max_abs_p_err"],
           by["zhu_boost_global_worst"]["psw_max"],
           by["zhu_boost_global_mid"]["rms_p_err"], best["code"],
           by["zhu_boost_global_bestRMS"]["rms_p_err"],
           by["ours_perrow_predistortion"]["rms_p_err"],
           by["ours_perrow_predistortion"]["max_abs_p_err"],
           round(by["zhu_boost_global_bestRMS"]["rms_p_err"]
                 / by["ours_perrow_predistortion"]["rms_p_err"]),
           by["ours_perrow_predistortion"]["mean_boost_mV"],
           by["zhu_boost_global_worst"]["mean_boost_mV"],
           by["no_comp"]["rms_p_err"], by["zhu_boost_global_worst"]["rms_p_err"],
           by["ours_perrow_predistortion"]["rms_p_err"], len(ROWS)))

    out = dict(
        _about=("Open-record-faithful reproduction of Zhu et al.'s line-resistance compensation "
                "(global voltage boost reading), run on OUR committed sMTJ write-path model. "
                "Numbers are computed by this script only (eda/design_survey/repro/zhu_boost.py)."),
        _paper=("Xi Zhu, Zhiwei Li, Haijun Liu, Qingjiang Li, Sen Liu, Nan Li, Hui Xu, 'Solution "
                "to alleviate the impact of line resistance on the crossbar array,' IET Circuits, "
                "Devices & Systems 14(4):498-504, 2020, DOI 10.1049/iet-cds.2019.0313."),
        _open_record=dict(
            fulltext_access="PAYWALLED at reproduction time (Wiley 402 / IET digital library 403)",
            abstract_quote_crossref=(
                "The crossbar array implementing the weighted sum computation and weight update "
                "operation is a promising hardware accelerator for neuromorphic computing. "
                "However, the voltage drop caused by the current flowing through the access lines "
                "could be aggressive for the resistive crossbar array in a fully parallel "
                "fashion. In this study, the authors analysed the impact of the line resistance "
                "on the crossbar array based on the SPICE simulation. It implies that the scale "
                "of the crossbar array and the ratio of line resistance to resistive random "
                "access memory resistance bring great influence on the performance of the "
                "crossbar array. Also an scheme of optimisation has been proposed to diminish "
                "its influence."),
            citation_context_quote_semanticscholar=(
                "Zhu et al. [35] linearly mapped the distorted current from the range of current "
                "of the extreme array with wire resistance to the range of current of the extreme "
                "array without wire resistance."),
            citation_context_source=("Qin et al., 'Design of High Robustness BNN Inference "
                                     "Accelerator Based on Binary Memristors,' 2020 (same NUDT "
                                     "group), via Semantic Scholar citation contexts")),
        _granularity_assumption=(
            "Per-position (per-row) granularity is NOT confirmable from the open record; the one "
            "substantive open description is a GLOBAL linear recalibration anchored at the array "
            "EXTREME. We therefore implement a GLOBAL write-voltage boost (one DAC code for all "
            "rows), evaluated at extreme-row and mid-row calibrations plus a full-code sweep that "
            "upper-bounds any global calibration. At a single write operating point a global "
            "linear map degenerates to a single offset, so the sweep covers the whole family. "
            "The node of application (input drive vs output current) is also not confirmable; we "
            "apply it to the only node our write path exposes, the shared drive voltage, and mark "
            "the crossbar-readout -> write-path transplant explicitly."),
        our_model_provenance=dict(
            source="eda/hero/ir_aware_writedac.py + ir_aware_writedac_summary.json (committed)",
            VTH=VTH, VT=VT, RSOT_ohm=RSOT, N=N, p_target=P_TARGET,
            V_target=round(V_TARGET, 4), I_write_mA=round(I_WRITE * 1e3, 3),
            R_par_formula="R_par(r) = 2*0.125 ohm/sq * (r*2.0um/1.0um)  [met2, Magic-extracted]",
            R_par_N_ohm=round(r_par(N), 1), IR_N_mV=round(ir(N) * 1e3, 2),
            dac_lsb_mV=round(LSB * 1e3, 4), dac_nbits=DAC["nbits"],
            dac_lsb_source="eda/hero/write_dac_resistor_string.json (measured sky130 sim)"),
        selfcheck_vs_committed=selfcheck,
        metric_definition=("residual write error = statistics of |P_sw(row) - p_target| over rows "
                           "r=0..N (257 positions), p_target=0.90; P_sw from the committed device "
                           "sigmoid; V_cell(r) = V_target + boost(r) - I_wr*R_par(r)"),
        schemes=schemes,
        global_boost_code_sweep=sweep,
        comparison_table_D3=dict(
            metric="residual write error: RMS (and max) |P_sw - 0.90| across the N=256 column",
            flow="committed write-path model (ir_aware_writedac.py constants), boosts quantized "
                 "to the measured 3.0411 mV resistor-string DAC LSB",
            designs=comparison_table),
        assumptions=[
            "GLOBAL granularity (see _granularity_assumption): per-row granularity for Zhu is not "
            "in the open record; a per-row variant under Zhu's name would coincide with our own "
            "design and would be an over-attribution.",
            "Context transplant: Zhu's paper compensates a crossbar weighted-sum READOUT; we "
            "apply the calibrated-global-IR-correction principle to our WRITE path's shared "
            "drive voltage (the only node the family can act on in our design).",
            "Fixed-current linearization IR(r)=I_wr*R_par(r) with I_wr=1.16 mA, inherited from "
            "the committed benchmark and applied IDENTICALLY to all schemes (boost does not "
            "change I_wr in this linearization).",
            "DAC quantization uses the measured resistor-string LSB (3.0411 mV) as an ideal "
            "uniform quantizer; INL (0.48 LSB measured) is neglected identically for all schemes.",
            "Zhu's headline metric (MNIST accuracy of a crossbar MLP) is not reproducible on a "
            "write path; the shared same-flow metric is the residual write error defined above.",
            "V_target places the near cell at p=0.90 (the committed benchmark's operating point).",
        ],
        integrity_caveats=(
            "Full text paywalled: the scheme is reconstructed from the abstract plus ONE citation "
            "context (quoted verbatim above); if the paper's actual scheme is finer-grained than "
            "global, the Zhu numbers here are a LOWER bound on its fidelity (and the full-code "
            "sweep shows the ceiling of any single-global-boost variant on this metric). The "
            "comparison is a principle-level transplant (crossbar readout -> write path), not a "
            "circuit-level reproduction of their SPICE testbench."),
        conclusion=concl)

    with open(HERE / "zhu_boost_summary.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2)

    # ---- console report -------------------------------------------------------------------------
    print("=" * 96)
    print("Zhu et al. 2020 (IET CDS, DOI 10.1049/iet-cds.2019.0313) global write-voltage boost")
    print("on OUR committed write path: N=%d, IR(N)=%.2f mV (%.1f V_T), DAC LSB=%.4f mV" %
          (N, ir(N) * 1e3, ir(N) / VT, LSB * 1e3))
    print("self-check vs committed ir_aware_writedac_summary.json: PASSED (spread %.4f == %.4f)" %
          (round(spread, 4), committed["psw_spread_nopd"]))
    print("=" * 96)
    hdr = "%-32s %9s %9s %9s %8s %9s %9s" % \
          ("scheme", "rmsPerr", "maxPerr", "spread", "Psw_min", "meanBoost", "maxBoost")
    print(hdr)
    for s in schemes:
        print("%-32s %9.4f %9.4f %9.4f %8.4f %8.2fmV %8.2fmV" %
              (s["scheme"], s["rms_p_err"], s["max_abs_p_err"], s["psw_spread"],
               s["psw_min"], s["mean_boost_mV"], s["max_boost_mV"]))
    print("-" * 96)
    print("global-boost sweep optimum: code %d (%.2f mV), RMS %.4f  [ceiling of ANY global cal]" %
          (best["code"], best["code"] * LSB * 1e3, best["rms_p_err"]))
    print("\n" + concl)
    print("\nwrote zhu_boost_summary.json")


if __name__ == "__main__":
    main()
