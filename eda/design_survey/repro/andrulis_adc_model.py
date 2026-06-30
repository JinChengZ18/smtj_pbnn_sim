#!/usr/bin/env python3
"""External-validation overlay: the Andrulis et al. ADC energy/area model, applied to OUR SAR points.

WHAT THIS IS
------------
A faithful re-implementation of the open-source ADC energy(-area)-vs-ENOB model from

    T. Andrulis, R. Chen, H.-S. Lee, J. S. Emer, V. Sze,
    "Modeling Analog-Digital-Converter Energy and Area for Compute-In-Memory Accelerator Design,"
    arXiv:2404.06553 (MIT). Open source: github.com/Accelergy-Project/accelergy-adc-plug-in

and an honest placement of OUR transient-measured sky130 SAR energy points relative to that
published law. It exists to migrate the "Andrulis ADC model" row OUT of the D.5 qualitative
capability matrix and turn it into a quantitative sanity-check of our D.4 numbers.

INTEGRITY POSTURE
-----------------
- The model form + every coefficient below is transcribed VERBATIM from the cited open source
  (model.py + headers.py + adc_data/model.yaml, branch `main`, fetched 2026-06-30). The exact
  equations implemented are quoted in METHOD_QUOTES at the bottom and in andrulis_adc_model_summary.json.
- Our energy points are read from our OWN committed JSON (sar_capdac_tran_summary.json,
  comparison_results.json). Nothing about our hardware is invented; every number this script
  emits is computed here.
- Where the paper's setting differs from ours (their 1997-2023 Murmann survey of COMPLETE ADCs,
  vs our PARTIAL energy = cap-DAC switching + comparator only; their ENOB vs our NOMINAL b; the
  unspecified throughput) the assumptions are documented in ASSUMPTIONS and carried into the JSON.

The comparison is framed as a ONE-SIDED LOWER-BOUND sanity check (see CAVEATS): our points are a
partial-energy SUBSET of a full ADC, and the Andrulis law is an OPTIMISTIC best-case bound for a
COMPLETE ADC. A faithful, defensible relationship between those two is "our partial energy must
not exceed their full-ADC best-case prediction" -- which is exactly what we test.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

# ============================================================================
# 1. THE ANDRULIS MODEL -- coefficients transcribed verbatim from the open source
#    github.com/Accelergy-Project/accelergy-adc-plug-in @ main
#    files: headers.py, model.py, adc_data/model.yaml  (fetched 2026-06-30)
# All of (tech node nm, frequency Hz) enter the model LOG-BASE-e-scaled (their headers.py
# LOGSCALE_PARAMS + model.yaml `comments:` field). Energy is returned in pJ/op.
# ============================================================================

# --- model.yaml : "FOMS_hf [dB]" block (the energy model) ---
_FOMS_FREQ_COEFF   = -2.8719030399529957   # FOMS_hf [dB] -> "frequency (Hz)"  (coeff on ln(freq))
_FOMS_INTERCEPT    = 213.7806687348118     # FOMS_hf [dB] -> "intercept"
_FOMS_MAX          = 164.7143258245858     # FOMS_hf [dB] -> "max value"   (global FOM_S clamp)
_FOMS_MAX_BY_ENOB  = [                      # FOMS_hf [dB] -> "max_by_enob" (index = ceil(ENOB))
    128.3068287398817, 131.52734025085925, 134.7478517618368, 137.96836327281437,
    141.18887478379193, 144.4093862947695, 147.62989780574708, 150.85040931672464,
    154.0709208277022, 157.29143233867975, 160.5119438496573, 163.73245536063487,
    166.95296687161243, 170.17347838259, 173.39398989356755, 176.61450140454514,
    179.83501291552267, 183.05552442650026, 186.27603593747781, 189.49654744845537,
    192.71705895943293,
]
_FOMS_TECH_INTERCEPT = 26.0496215686518     # FOMS_hf [dB] -> "tech intercept"
_FOMS_TECH_SLOPE     = 1.8800369206815004   # FOMS_hf [dB] -> "tech slope"   (coeff on ln(tech nm))
_FOMS_ENOB_SLOPE     = -2.8291256050594527  # FOMS_hf [dB] -> "enob slope"   (coeff on ln(ENOB))
_FOMS_ENRG_RESIDUAL  = -1.4702022133784405  # FOMS_hf [dB] -> "energy (pJ/op) res"
_FREQ_MAX_LN         = 23.025850929940457   # "frequency (Hz)" -> "max value" = ln(1e10)

# --- model.yaml : "area (um^2)" block (the area model = paper Eq. 1) ---
_AREA_TECH   = 0.9932794744745022   # area (um^2) -> "tech node (nm)"   (~1.0 in paper Eq.1)
_AREA_FREQ   = 0.18071538424508238  # area (um^2) -> "frequency (Hz)"   (~0.2 in paper Eq.1)
_AREA_ENRG   = 0.29912426192653485  # area (um^2) -> "energy (pJ/op)"   (~0.3 in paper Eq.1)
_AREA_INTER  = 1.3461916439910742   # area (um^2) -> "intercept"


def bits2sndr(bits: float) -> float:
    """SNDR [dB] from resolution. headers.py bits2sndr(): bits*20*log10(2) + 10*log10(1.5).
    == the textbook ideal SNDR = 6.0206*N + 1.7609 dB."""
    return bits * 20.0 * math.log(2, 10) + 10.0 * math.log(1.5, 10)


def foms_sndr2energy(foms: float, sndr: float) -> float:
    """Energy [pJ/op] from Schreier FOM_S and SNDR. model.py foms_sndr2energy():
    return 1 / ((10 ** ((foms - sndr) / 10)) * 2).
    (Inverts FOM_S = SNDR + 10*log10(f_s/P): E = P/f_s = 1 / (2 * 10**((FOM_S - SNDR)/10)).)"""
    return 1.0 / ((10.0 ** ((foms - sndr) / 10.0)) * 2.0)


def get_energy(enob: float, freq_hz: float, tech_nm: float,
               allow_extrapolation: bool = True) -> float:
    """ADC energy per conversion [pJ/op]. Faithful port of model.py get_energy().

    foms = INTERCEPT + FREQ_COEFF * ln(freq)            (clamped by max_by_enob[ceil(ENOB)])
    energy = foms_sndr2energy(foms, bits2sndr(ENOB))
             * exp(TECH_INTERCEPT + TECH_SLOPE*ln(tech) + ENOB_SLOPE*ln(ENOB) + ENRG_RESIDUAL)
    """
    ln_freq = math.log(freq_hz)
    if not allow_extrapolation:
        assert ln_freq <= _FREQ_MAX_LN, "freq above model max; enable extrapolation"
    foms = _FOMS_INTERCEPT + _FOMS_FREQ_COEFF * ln_freq
    # clamp by per-ENOB FOM_S ceiling (model.py: index = max(min(ceil(ENOB), len-1), 0))
    idx = max(min(math.ceil(enob), len(_FOMS_MAX_BY_ENOB) - 1), 0)
    foms = min(foms, _FOMS_MAX_BY_ENOB[idx])
    energy_pj = foms_sndr2energy(foms, bits2sndr(enob))
    return energy_pj * math.exp(
        _FOMS_TECH_INTERCEPT
        + _FOMS_TECH_SLOPE * math.log(tech_nm)
        + _FOMS_ENOB_SLOPE * math.log(enob)
        + _FOMS_ENRG_RESIDUAL
    )


def get_area(enob: float, freq_hz: float, tech_nm: float, energy_pj: float) -> float:
    """ADC area [um^2]. Faithful port of model.py get_area() (= paper Eq. 1 in log space):
    area = exp(intercept + a_tech*ln(tech) + a_freq*ln(freq) + a_enrg*ln(energy_pJ))."""
    return math.exp(
        _AREA_INTER
        + _AREA_TECH * math.log(tech_nm)
        + _AREA_FREQ * math.log(freq_hz)
        + _AREA_ENRG * math.log(energy_pj)
    )


# ============================================================================
# 2. OUR MEASURED POINTS -- read from our OWN committed JSON
# ============================================================================
REPO = Path(__file__).resolve().parents[3]            # .../smtj_pbnn_sim
SAR_JSON = REPO / "eda" / "testbenches" / "sar_capdac_tran_summary.json"
CMP_JSON = REPO / "eda" / "design_survey" / "comparison_results.json"
FIGDIR   = REPO / "article" / "figs"
OUT_JSON = Path(__file__).resolve().parent / "andrulis_adc_model_summary.json"

# Our SAR energy-measurement settling window (sar_capdac_tran.py: TSTEP = 5e-9 s per bit-trial).
# It is NOT a designed throughput target; it is the per-bit settling window of the energy
# transient. We derive an implied conversion rate f_s = 1 / (b * TSTEP) only so the (throughput-
# dependent) Andrulis law CAN be evaluated, and we report a throughput-sensitivity band (1e6..1e9).
TSTEP_S = 5e-9
TECH_NM = 130.0   # our flow is sky130 == 130 nm; Andrulis tech param is ln(nm), evaluated at 130.


def load_our_points():
    sar = json.loads(SAR_JSON.read_text(encoding="utf-8"))
    e_comp_fj = float(sar["E_comp_fJ_extracted"])     # 48 fJ/decision (extracted StrongARM)
    pts = []
    for row in sar["rows"]:
        b = int(row["b"])
        # OUR total measured energy/conversion = transient cap-DAC switching + b*comparator
        e_total_fj = float(row["E_total_fJ"])         # already = E_capdac_meas + b*E_comp
        f_s = 1.0 / (b * TSTEP_S)                      # implied conversion rate (documented assumption)
        pts.append({
            "b": b,
            "scheme": row["scheme"],
            "E_capdac_fJ_measured": float(row["E_capdac_fJ_measured"]),
            "E_comp_fJ": float(row["E_comp_fJ"]),
            "E_total_fJ_ours": e_total_fj,
            "implied_f_s_Hz": f_s,
        })
    return e_comp_fj, pts


# ============================================================================
# 3. COMPARE: where do our (ENOB~b, fJ/conv) points fall on the published law?
# ============================================================================
def compare():
    e_comp_fj, pts = load_our_points()
    results = []
    for p in pts:
        b = p["b"]
        f_s = p["implied_f_s_Hz"]
        # Andrulis prediction at our operating point (ENOB := nominal b; see ASSUMPTIONS)
        pred_pj = get_energy(enob=b, freq_hz=f_s, tech_nm=TECH_NM)
        pred_fj = pred_pj * 1e3
        pred_area_um2 = get_area(enob=b, freq_hz=f_s, tech_nm=TECH_NM, energy_pj=pred_pj)
        ours_fj = p["E_total_fJ_ours"]
        ratio = ours_fj / pred_fj                      # ours / Andrulis-full-ADC-best-case
        results.append({
            **p,
            "andrulis_pred_E_fJ_full_ADC": pred_fj,
            "andrulis_pred_area_um2": pred_area_um2,
            "ratio_ours_over_andrulis": ratio,
            # one-sided sanity test: a partial-energy subset of a full ADC should not exceed the
            # full-ADC OPTIMISTIC best-case prediction.
            "consistent_as_lower_bound": ours_fj <= pred_fj,
        })
    # throughput-sensitivity band (the one materially under-specified input)
    sens = []
    for fs in (1e6, 1e7, 1e8, 1e9):
        row = {"f_s_Hz": fs}
        for b in (6, 7, 8):
            row[f"pred_fJ_b{b}"] = get_energy(enob=b, freq_hz=fs, tech_nm=TECH_NM) * 1e3
        sens.append(row)
    return e_comp_fj, results, sens


# ============================================================================
# 4. FIGURE (only emitted because the mapping is faithful as a lower-bound check)
# ============================================================================
def make_figure(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(6.4, 4.4))

    # Andrulis full-ADC best-case law at our 130 nm node, evaluated at EACH point's implied f_s.
    # The model is only meaningfully evaluated at integer ENOB here (our nominal b; the per-ENOB
    # FOM_S clamp is step-wise in ceil(ENOB)), so we plot the law as discrete predictions at the
    # integer b we actually test, connected for the eye -- NOT a fractional-ENOB curve.
    bs = sorted({r["b"] for r in results})
    law_fj = [get_energy(b, 1.0 / (b * TSTEP_S), TECH_NM) * 1e3 for b in bs]
    ax.plot(bs, law_fj, "D--", color="0.45", lw=1.6, ms=7, mfc="0.7",
            label="Andrulis best-case full ADC\n(130 nm, $f_s$=1/($b\\cdot$5 ns))")

    schemes = sorted({r["scheme"] for r in results})
    markers = {"conventional": "o", "monotonic": "s"}
    colors = {"conventional": "#c44", "monotonic": "#268"}
    for sch in schemes:
        xs = [r["b"] for r in results if r["scheme"] == sch]
        ys = [r["E_total_fJ_ours"] for r in results if r["scheme"] == sch]
        ax.plot(xs, ys, markers.get(sch, "^"), color=colors.get(sch, "#444"),
                ms=8, ls="none", label="ours: %s SAR\n(cap-DAC$_{tran}$ + $b\\times$48 fJ)" % sch)

    ax.set_yscale("log")
    ax.set_xlabel("resolution  ($b \\approx$ ENOB, nominal)")
    ax.set_ylabel("energy per conversion (fJ)")
    ax.set_title("Sanity check: our partial SAR energy vs Andrulis full-ADC best-case law")
    ax.grid(True, which="both", ls=":", alpha=0.4)
    ax.legend(fontsize=7.5, loc="upper left", framealpha=0.9)
    ax.text(0.98, 0.03,
            "ours = cap-DAC switching (sky130 transient) + comparator only;\n"
            "Andrulis = optimistic full ADC. Ours below the line = consistent (partial < full).",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6.3, color="0.35")
    fig.tight_layout()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    out = FIGDIR / "AppendixD_06.png"
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return str(out)


METHOD_QUOTES = {
    "source": "github.com/Accelergy-Project/accelergy-adc-plug-in @ main (headers.py, model.py, "
              "adc_data/model.yaml); paper arXiv:2404.06553.",
    "bits2sndr": "headers.py: return bits * 20 * math.log(2, 10) + 10 * math.log(1.5, 10)  "
                 "(== ideal SNDR = 6.02*N + 1.76 dB).",
    "foms_sndr2energy": "model.py: return 1 / ((10 ** ((foms - sndr) / 10)) * 2)  "
                        "(inverts Schreier FOM_S = SNDR + 10*log10(f_s/P) for E[pJ/op]).",
    "get_energy": "model.py: foms = sum(params[k]*model[FOMS][k] for k in [INTERCEPT, FREQ]); "
                  "foms = min(foms, foms_max_by_enob[ceil(ENOB)]); "
                  "energy = foms_sndr2energy(foms, bits2sndr(ENOB)) * exp(TECH_INTERCEPT + "
                  "TECH_SLOPE*params[TECH] + ENOB_SLOPE*log(ENOB) + ENRG_RESIDUAL); "
                  "params[TECH]=ln(tech_nm), params[FREQ]=ln(freq_Hz).",
    "get_area_eq1": "paper Eq.1: Area(um^2) = 21.1 * Tech(nm)^1.0 * Throughput^0.2 * "
                    "(Energy(pJ)/Convert)^0.3; model.yaml exponents = "
                    "tech 0.9933, freq 0.1807, energy 0.2991 (log-space intercept 1.3462).",
    "tech_and_throughput": "model.yaml comments: 'Tech node, area, and frequency are "
                           "log-base-e-scaled.' Reference/visualization node 32 nm; the model "
                           "takes tech_nm as a free log-scaled input, evaluated here at 130 nm.",
}


def main():
    e_comp_fj, results, sens = compare()
    fig_path = make_figure(results)

    n_pass = sum(1 for r in results if r["consistent_as_lower_bound"])
    n_tot = len(results)
    ratios = [r["ratio_ours_over_andrulis"] for r in results]
    verdict = (
        f"{n_pass}/{n_tot} of our SAR points pass the one-sided lower-bound test "
        f"(our partial energy <= Andrulis full-ADC best case). "
        f"ours/Andrulis ratio range [{min(ratios):.4f}, {max(ratios):.4f}]. "
        + ("All points consistent: our measured SAR energy sits below the optimistic full-ADC "
           "law, as a partial energy must -- the D.4 numbers are sane against the cited model."
           if n_pass == n_tot else
           "WARNING: one or more points EXCEED the full-ADC best-case law -- investigate; a "
           "partial energy above an optimistic full-ADC bound is a red flag.")
    )

    summary = {
        "_about": "External-validation overlay of the Andrulis et al. (arXiv:2404.06553) ADC "
                  "energy/area-vs-ENOB model, with OUR transient-measured sky130 SAR energy "
                  "points placed on it. Runnable script: andrulis_adc_model.py. Migrates the "
                  "'Andrulis ADC model' row out of the D.5 capability matrix into a quantitative "
                  "lower-bound sanity-check of the D.4 SAR energy numbers.",
        "model_source": METHOD_QUOTES["source"],
        "method_quotes": METHOD_QUOTES,
        "model_coefficients_verbatim_from_model_yaml": {
            "FOMS_freq_coeff": _FOMS_FREQ_COEFF, "FOMS_intercept": _FOMS_INTERCEPT,
            "FOMS_max": _FOMS_MAX, "FOMS_tech_intercept": _FOMS_TECH_INTERCEPT,
            "FOMS_tech_slope": _FOMS_TECH_SLOPE, "FOMS_enob_slope": _FOMS_ENOB_SLOPE,
            "FOMS_enrg_residual": _FOMS_ENRG_RESIDUAL, "freq_max_ln": _FREQ_MAX_LN,
            "area_tech": _AREA_TECH, "area_freq": _AREA_FREQ, "area_enrg": _AREA_ENRG,
            "area_intercept": _AREA_INTER,
        },
        "our_inputs": {
            "tech_nm": TECH_NM, "TSTEP_s_per_bit": TSTEP_S,
            "E_comp_fJ_per_decision": e_comp_fj,
            "E_total_per_conversion": "cap-DAC transient switching (sky130) + b*48 fJ comparator, "
                                      "read verbatim from sar_capdac_tran_summary.json rows.",
        },
        "comparison": results,
        "throughput_sensitivity_pred_fJ": sens,
        "figure": fig_path,
        "assumptions": ASSUMPTIONS,
        "integrity_caveats": CAVEATS,
        "verdict": verdict,
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {fig_path}")
    for r in results:
        print(f"  b={r['b']:>2} {r['scheme']:<12} ours={r['E_total_fJ_ours']:8.1f} fJ  "
              f"andrulis={r['andrulis_pred_E_fJ_full_ADC']:10.1f} fJ  "
              f"ratio={r['ratio_ours_over_andrulis']:7.4f}  "
              f"consistent={r['consistent_as_lower_bound']}")


ASSUMPTIONS = [
    "ENOB := nominal resolution b (6,7,8). We did NOT measure a code-density/FFT ENOB; the "
    "Andrulis ENOB axis is filled with our nominal b. This OVER-states our ENOB if real ENOB < b, "
    "which makes the Andrulis prediction an UPPER estimate and our partial energy even more "
    "comfortably below it -- it does not threaten the one-sided lower-bound test.",
    "tech_nm = 130 (sky130). Andrulis calibrate/visualize at 32 nm but expose tech as a free "
    "log-scaled input (tech slope 1.88 on ln(nm)); 130 nm is an EXTRAPOLATION above their "
    "32 nm reference but within the survey's historical node range, so it is in-model, not invented.",
    "Throughput f_s := 1/(b*TSTEP) with TSTEP=5 ns from sar_capdac_tran.py (per-bit settling "
    "window of OUR energy transient), NOT a designed conversion-rate target. Because the Andrulis "
    "energy law is throughput-dependent, a throughput-sensitivity band (1e6..1e9 Hz) is reported "
    "so the conclusion can be read independent of this single under-specified input.",
    "Our energy is PARTIAL: transient cap-DAC switching (sky130) + extracted comparator (b*48 fJ) "
    "ONLY. It excludes SAR control logic, sample/hold, and reference buffer. The Andrulis number "
    "is a COMPLETE-ADC best-case. The comparison is therefore one-sided (partial <= full), not an "
    "equality match.",
]

CAVEATS = (
    "This is a LOWER-BOUND sanity check, not a like-for-like reproduction. (1) Domain mismatch: "
    "the Andrulis law predicts a COMPLETE ADC's energy from a survey of complete ADCs; our points "
    "are a PARTIAL energy (cap-DAC switching + comparator only), so they can only be tested as "
    "'must not exceed' the full-ADC optimistic bound, not equated to it. (2) ENOB is nominal b, "
    "not measured. (3) Throughput is an implied settling-window rate, not a designed f_s; hence "
    "the sensitivity band. (4) 130 nm is an extrapolation above their 32 nm calibration node. "
    "Within those bounds the test is faithful: if our partial energy already exceeded their "
    "full-ADC best case, our numbers would be suspect; the script reports whether each point "
    "passes that test. Reproduce: rerun this script (pure-python; matplotlib only for the figure)."
)

if __name__ == "__main__":
    main()
