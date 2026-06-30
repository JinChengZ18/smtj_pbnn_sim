# D.5 Substantiation Plan — Grounded Capability Matrix, Reviewer-Risk Triage, and Reproduction Roadmap

This plan converts the per-design grounding results into a defensible form of the D.5 qualitative capability matrix. Each non-N mark is given a one-line cited justification; cells that the grounding could not defend are flagged for downgrade or drop; and the designs are ranked by same-flow reproduction feasibility so that as many qualitative rows as possible can be migrated into the quantitative D.2–D.4 tables.

Legend: `Y` = directly addresses the capability; `~` = partially / by analogy; `N` = not addressed. `[lo]` = low-confidence verdict (defensible either way, the safer mark is shown); all other non-N marks are high confidence unless noted.

Mapping to the current appendix tables: D.5 readout = table D.4 (current file lines 62–68); D.5 write = table D.5 (lines 72–80); D.5 SAR = table D.6 (lines 84–92).

---

## 1. Corrected / grounded matrix

### 1.1 Readout sense-amplifier (table D.4)

Columns: offset-vs-V_T | XNOR-popcount | shared/amortized ADC | resistive-MTJ read load | SOT write-line IR | silicon-measured

| Design | off/V_T | XNOR-pc | shared ADC | resistive-MTJ | SOT-IR | silicon | Net change vs current |
|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Dong single-cap auto-zeroed SA | N | N | N | Y | N | Y | unchanged (N N N Y N Y) |
| Xcel-RAM SRAM XNOR | N | Y | Y | N | N | **N** | col 6 Y→N |
| RRAM XNOR-BNN macro | N | Y | Y | **~** | N | Y | col 4 Y→~ |
| current-sampling SA | **~** | N | N | **~** | N | Y | col 1 N→~, col 4 Y→~ |

Per non-N cell, cited justification (one line each):

- **Dong — resistive-MTJ (Y):** explicitly a 1T1MTJ STT-MRAM read; SA senses cell current against `Vref = 2*Iread*(RP||RAP)` (Dong et al., ISSCC 2018 30.2 / JSSC DOI 10.1109/JSSC.2018.2872584).
- **Dong — silicon-measured (Y):** fabricated 28 nm 1 Mb macro, measured 2.8 ns@25 °C / 3.6 ns@120 °C read, RER ~1e-5 (same cite).
- **Xcel-RAM — XNOR-popcount (Y):** abstract verbatim "charge sharing XNOR and popcount operation in 10 transistor SRAM cells" (Agrawal et al., arXiv:1807.00343; TCAS-I DOI 10.1109/TCSI.2019.2899838).
- **Xcel-RAM — shared ADC (Y):** RBL-switched sectioning runs many parallel convolutions per cycle, amortizing the dual-stage ADC + precharge (~2.5× energy / 4× perf) (same cite).
- **RRAM XNOR-BNN — XNOR-popcount (Y):** XNOR-RRAM asserts all 128 WLs, analog popcount along bitlines (Yin et al., IEEE TED 67(10):4185–4192, 2020, DOI 10.1109/TED.2020.3013182).
- **RRAM XNOR-BNN — shared ADC (Y):** eight 8-to-1 column muxes feed eight 3-bit flash ADCs for 64 bitlines = one ADC per 8 columns (same cite; testchip detail par.nsf.gov/servlets/purl/10063211).
- **RRAM XNOR-BNN — resistive-MTJ (~):** resistive read load is genuine (1T1R HRS/LRS bitline divider), but the device is RRAM, not MTJ — partial.
- **RRAM XNOR-BNN — silicon-measured (Y):** 90 nm CMOS prototype with monolithic RRAM, measured 24 TOPS/W, 98.5% MNIST (same cite).
- **current-sampling SA — offset-vs-V_T (~):** paper targets/reduces input-referred offset, but against an R-ratio / current sensing margin, not an absolute V_T window, and the open abstract gives no mV (Chang et al., IEEE JSSC 48(3):864–877, 2013, DOI 10.1109/JSSC.2012.2235013). `[lo]`
- **current-sampling SA — resistive-MTJ (~):** measured vehicle is a 90 nm 512 Kb OTP small-cell-current NVM, not an MTJ; current-mode small-cell regime is the relevant analog only (same cite). `[lo]`
- **current-sampling SA — silicon-measured (Y):** fabricated 90 nm 512 Kb OTP macro, measured 26 ns access, sub-200 nA cell (same cite).

Our own row (TIA + StrongARM, sky130) is unchanged and stays `✓ ✓ ✓ ✓ ✓ ✗` per the existing file.

### 1.2 Write path (table D.5)

Columns: per-row IR prediction/pre-distortion | DAC topology + write rail | write-energy accounting | binary P_sw target | V_th trim | sMTJ device

| Design | IR predist | DAC+rail | write-E | bin P_sw | V_th trim | sMTJ dev | Net change vs current |
|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Truong parasitic-adapted | **Y** | N | N | N | N | N | col 1 ~→Y |
| Zhu positional-boost | ~ | N | N | N | N | N | unchanged (~ N N N N N) |
| Kim water-filling | N | N | Y | **~** | N | N | col 4 N→~ `[lo]` |
| Chen–Dolecek 1S1R model | **~** | N | N | N | N | N | col 1 N→~ |
| VECOM encode + SA trim | N | **N** | N | N | **~** | N | col 2 ~→N, col 5 Y→~ |
| Yoon sMTJ p-bit driver | N | ~ | N | **~** | **Y** | Y | col 4 Y→~ `[lo]`, col 5 ~→Y |

Per non-N cell, cited justification:

- **Truong — IR predist (Y):** core method predicts per-cell wire-R by superposition `R_{j,i}=ir+(m-j+1)r` and pre-distorts the programmed map (Eq.6); recognition ~100%@3.0 Ω vs 65% uncompensated, model-vs-SPICE <2.9% (Truong, Materials 12(24):4097, 2019, DOI 10.3390/ma12244097).
- **Zhu — IR predist (~):** SPICE line-R IR analysis + a compensating voltage-boost scheme, but per-row granularity / position-indexed pre-distortion not confirmed in the open abstract (Zhu et al., IET CDS 14(4):498–504, 2020, DOI 10.1049/iet-cds.2019.0313). `[lo]`
- **Kim — write-energy (Y):** energy/latency-constrained write-fidelity optimization, "40% write energy reduction for a given classification accuracy" (Kim et al., arXiv:2112.02842, 2021; ISIT 2020 DOI 10.1109/ISIT44484.2020.9173990).
- **Kim — binary P_sw (~):** model is built on per-bit write-error/switching probability but optimizes digital-word MSE fidelity, not a binary device P_sw target — related/partial (same cite). `[lo]`
- **Chen–Dolecek — IR predist (~):** derives position-dependent write-voltage attenuation + per-cell write-BER (prediction yes); remedy is BCH/location-dependent coding, not voltage pre-distortion (no compensation) (Chen & Dolecek, arXiv:1912.02963, 2019; companion arXiv:2104.14011, 2021).
- **VECOM — V_th trim (~):** "offset compensation" is conductance-domain remap during programming (`G'=G+G00`, subtract `N*I00` via one HRS column), NOT a comparator/ADC threshold trim — partial only (Jang et al., VECOM, ICCAD 2023; arXiv:2312.11042).
- **Yoon — DAC+rail (~):** no DAC (bias is a manually-swept DC gate voltage), but a concrete driver stage + 1.8 V rail / 0–1.8 V swing are reported — rail half satisfied (Yoon et al., arXiv:2604.14446, 2026; IEEE EDL 2026).
- **Yoon — binary P_sw (~):** demonstrates a tunable two-level fluctuating digital output, but reports no numeric P_sw target or sigmoid curve — controllable binary output, not write-to-target (same cite). `[lo]`
- **Yoon — V_th trim (Y):** working VTC sets inverter threshold 0.7→1.1 V in 100 mV steps — explicit fabricated tunable trim (same cite).
- **Yoon — sMTJ device (Y):** real sMTJ integrated with 130 nm commercial CMOS via BEOL, fabricated and measured (same cite).

Our own row (resistor-string DAC + IR pre-distortion) is unchanged at `✓ ✓ ✓ ✓ ✓ ✓`.

### 1.3 SAR readout (table D.6)

Columns: extracted comparator energy | offset-vs-V_T | column-shared/amortized | pure charge-redistribution SAR | comparator/cap-DAC energy split | RC-or-CIM

| Design | comp-E | off/V_T | col-shared | pure CR-SAR | comp/DAC split | RC/CIM | Net change vs current |
|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| Liu–Zhang SAR/SS | N | N | Y | ~ | N | Y | unchanged (N N Y ~ N Y) |
| PICO-RAM time-domain ADC | N | **N** | **Y** | N | N | Y | col 2 ~→N, col 3 ~→Y |
| Andrulis ADC energy model | N | N | N | N | **N** | Y | col 5 ~→N |
| Dutta StrongARM-SAR | ~ | N | N | **~** | N | N | col 4 Y→~ |
| Zhong memristor RC | N | N | N | N | N | Y | unchanged (N N N N N Y) |
| image-sensor SAR/SS | N | N | Y | ~ | N | N | unchanged (N N Y ~ N N) |

Per non-N cell, cited justification:

- **Liu–Zhang — column-shared (Y):** "column-parallel time-interleaved" converter; comparator shared SAR/SS, single-slope ramp shared globally (Liu et al., IEEE AICAS 2023, DOI 10.1109/AICAS57966.2023.10168604).
- **Liu–Zhang — pure CR-SAR (~):** SAR+single-slope hybrid; charge-redistribution SAR resolves MSBs only, SS resolves LSBs (same cite).
- **Liu–Zhang — RC/CIM (Y):** explicitly a reconfigurable ADC for Computing-in-Memory quantization (same cite).
- **PICO-RAM — column-shared (Y):** 8-phase ring oscillator shared across 8 local TD-ADCs + comparator power-gating (55.8% local-ADC energy, no accuracy loss) (Zhiyu Chen et al., IEEE JSSC 60:308, 2025; arXiv:2407.12829).
- **PICO-RAM — RC/CIM (Y):** charge-domain analog CIM SRAM macro, 40.2 TOPS/W, 90.7% CIFAR-10 (same cite).
- **Andrulis — RC/CIM (Y):** architecture-level ADC energy/area model explicitly for analog CIM/RRAM accelerators (Andrulis et al., arXiv:2404.06553, 2024).
- **Dutta — extracted comparator energy (~):** reports a ~6% PDP reduction (relative), no absolute fJ/decision — related/partial (Dutta, arXiv:2209.07259, 2022).
- **Dutta — pure CR-SAR (~):** comparator designed *for* a SAR-ADC but only the comparator is built; no cap-DAC loop implemented — partial (same cite).
- **Zhong — RC/CIM (Y):** fully-analogue memristor reservoir-computing system, 96.6% arrhythmia / 97.9% gesture (Zhong et al., Nature Electronics 5:672–681, 2022, DOI 10.1038/s41928-022-00838-3).
- **image-sensor — column-shared (Y):** "a comparator is shared in each column, and a 6-bit ramp generator is shared by all columns" (Zhang et al., IEICE Trans. Fund. E101.A(2):434–437, 2018, DOI 10.1587/transfun.E101.A.434).
- **image-sensor — pure CR-SAR (~):** two-step SAR/SS hybrid; SAR resolves upper 6 bits, single-slope the lower 6 (same cite).

Our own row (column-shared SAR) is unchanged at `✓ ✓ ✓ ✓ ✓ ✓`.

### 1.4 Low-confidence cells (must be flagged in the thesis)

These five cells are defensible but a reviewer could argue the opposite mark; flag each with a footnote noting the basis is an abstract/paywalled-snippet inference:

1. **current-sampling SA — offset-vs-V_T (~)** — JSSC full text paywalled; offset target real but no absolute mV and against an R-ratio margin.
2. **current-sampling SA — resistive-MTJ (~)** — OTP/NVM load, not MTJ; analogy only.
3. **Kim — binary P_sw (~)** — per-bit switching probability engaged, but objective is digital-word MSE, not a device P_sw target; could equally be N.
4. **Zhu — IR predist (~)** — paywalled; per-row granularity unconfirmed; voltage-boost end of the family.
5. **Yoon — binary P_sw (~)** — tunable binary output demonstrated, but no numeric P_sw target/curve; could be argued Y if narrowed to "controllable binary probabilistic output."

---

## 2. Reviewer-risk triage

### 2.1 Marks that the grounding could NOT defend — fix before submission

These are the highest-priority corrections; leaving them as-is is a factual error a reviewer can refute from the abstract/title alone.

| # | Cell (table) | Current | Grounded | Why indefensible | Action |
|---|---|:--:|:--:|---|---|
| R1 | Xcel-RAM — silicon-measured (D.4) | ✓ | **N** | Paper is HSPICE 45 nm PTM + CACTI; no fabricated chip. Per-op fJ are simulated. | **Flip ✓→✗.** Hard error. |
| R2 | VECOM — V_th trim (D.5) | ✓ | **~** | "Offset compensation" is conductance-domain remap during programming, not a comparator/ADC V_th trim. | **Soften ✓→∼** (or N). |
| R3 | VECOM — DAC+rail (D.5) | ∼ | **N** | Read/encode-side technique; no driver/DAC/rail content. | **Soften ∼→✗.** |
| R4 | Andrulis — comp/cap-DAC split (D.6) | ∼ | **N** | Whole-ADC energy only; explicitly abstracts circuit details, no component split. | **Soften ∼→✗.** |
| R5 | Yoon — binary P_sw (D.5) | ✓ | **~** | No numeric P_sw target/curve; only a tunable binary output. | **Soften ✓→∼.** |
| R6 | Dutta — pure CR-SAR (D.6) | ✓ | **~** | Comparator-only; no charge-redistribution cap-DAC implemented. | **Soften ✓→∼** (or footnote "intended ADC context"). |
| R7 | RRAM XNOR-BNN — resistive-MTJ (D.4) | ✓ | **~** | Resistive load is RRAM, not MTJ; literal "MTJ" overclaims. | **Soften ✓→∼.** |
| R8 | current-sampling SA — resistive-MTJ (D.4) | ✓ | **~** | OTP NVM load, not MTJ. | **Soften ✓→∼.** |

### 2.2 Marks that should be *upgraded* (currently understated — defensible to strengthen)

| # | Cell (table) | Current | Grounded | Basis |
|---|---|:--:|:--:|---|
| U1 | Truong — IR predist (D.5) | ∼ | **Y** | Per-cell IR prediction + pre-distortion *is* the entire contribution (verbatim from open PMC full text). |
| U2 | Chen–Dolecek — IR predist (D.5) | ✗ | **~** | Explicit position-dependent write-V attenuation + per-cell write-BER (prediction, not compensation). |
| U3 | Kim — binary P_sw (D.5) | ✗ | **~** | Built on per-bit switching probability. `[lo]` |
| U4 | Yoon — V_th trim (D.5) | ∼ | **Y** | Fabricated VTC, 0.7–1.1 V / 100 mV steps. |
| U5 | current-sampling SA — offset-vs-V_T (D.4) | ✗ | **~** | Paper genuinely targets input-referred offset. `[lo]` |
| U6 | PICO-RAM — column-shared (D.6) | ∼ | **Y** | Shared RO across 8 ADCs + comparator power-gating, quantified 55.8%. |

### 2.3 Most-likely-to-be-challenged marks (rank order)

1. **Any "silicon-measured" ✓ on a CIM macro paper** — the Roy-group / CIM lineage (Xcel-RAM here) is frequently PTM/HSPICE, not taped out. Xcel-RAM R1 is the concrete failure; a reviewer who knows this family will check every silicon column. *Defense:* verify against the methodology section, not per-op energy; we already corrected the one bad cell.
2. **"resistive-MTJ read load" ✓ on RRAM/OTP designs** — the column header literally says MTJ; RRAM/OTP loads are an analogy. R7/R8. *Defense:* downgrade to ∼ and footnote "resistive-read-load class, not MTJ device."
3. **Our own row showing ✓ across almost every column** — a reviewer may read the all-✓ rows (D.4/D.5/D.6 line 1) as self-serving. *Defense:* our ✓ are backed by the D.2–D.4 *measured* same-flow data + the device-calibrated P_sw model; cite those tables inline from the matrix caption.
4. **Citation-attribution slips already in the file** — comparison block still labels Chen–Dolecek as "Cassuto 1S1R 2019" and PICO-RAM as "Zhang 2024"; the design is Zhiyu Chen et al. These are cosmetic but undermine credibility if spotted. *Defense:* relabel in `submodule_survey.json` comparison rows.
5. **V/2-vs-V/3 over-attribution to Chen–Dolecek** — the survey attributes a V/2-vs-V/3 biasing claim to arXiv:1912.02963 that is not in that paper. *Defense:* if any panel/appendix text leans on it, recite to a genuine half-select reference or drop.
6. **Zhong "ADC quantizes read currents" claim** — the cited Nature Electronics system is fully analogue with no ADC; the survey "approach" field overstates it. The five SAR columns are correctly N, but the *motivation framing* must be corrected to "a fully-analogue RC demonstration that motivates why digitizing reservoir states is costly," not "evidence an ADC must be amortized."
7. **All `[lo]` cells (§1.4)** — paywalled-abstract inferences. *Defense:* footnote the evidence level.

### 2.4 Rows that could be dropped (optional, for a leaner matrix)

- **Andrulis ADC energy model** and **Zhong memristor RC** each survive on a *single* ✓ (RC/CIM) with everything else N. They anchor the "ADC sits at the analog/digital boundary / RC use-case" context but add little discriminating power. *Option:* keep (they motivate the axis) but consider merging the all-but-one-N rows into a short prose sentence if the matrix is judged too sparse. Recommendation: **keep**, because they justify why the RC/CIM column exists.

---

## 3. Reproduction roadmap (path to retire the qualitative matrix)

Ranked by effort (low first). Each entry names the concrete same-flow sub-block to build and which existing fixture / output it plugs into. "Algorithm-on-model" = runs on the repo's calibrated sMTJ/energy model, not sky130; "sub-block" = sky130 + ngspice netlist through an existing fixture.

### Tier 0 — LOW effort (do first; highest yield per hour)

1. **Kim water-filling (write-energy, RC/CIM)** — algorithm-on-model.
   - Build: iterative water-filling / KKT non-uniform write-pulse allocation on top of the repo's existing sMTJ write-energy + P_sw(write-error) model.
   - Output: write-energy-vs-fidelity (or vs MNIST accuracy) operating point + energy-reduction factor at fixed accuracy → a quantitative point on the **write-energy axis** of D.3.
   - Reuses: existing write-energy accounting; no new netlist.

2. **Andrulis ADC energy model (energy-vs-ENOB)** — algorithm-on-model.
   - Build: re-implement the published piecewise regression (energy exponential in ENOB, area ~ E^0.3) as a small Python function; overlay our measured StrongARM/SAR points.
   - Output: external sanity-check curve placing our D.4 fJ/conv on the published energy-vs-resolution law; reconciles "comparator b-linear vs whole-ADC exponential."
   - Reuses: `comparison_results.json` points; MIT model is open-source.

3. **Dutta StrongARM-SAR (offset, comparator energy)** — sub-block, drop-in.
   - Build: re-netlist the StrongARM-as-SAR-decision-element in sky130; run through the **existing** `run_offset_mc.py` offset-MC fixture (σ_off/V_T, N≈120) and the extracted-energy script (`sa_postlayout.py`); optionally into `sar_capdac_tran.py`.
   - Output: measured offset-vs-V_T + extracted comparator fJ for a Dutta-style comparator, sitting alongside our three comparators in D.2 (ours-flow-vs-ours-flow; Dutta gives only relative numbers).
   - Reuses: comparator offset-MC factory verbatim. Caveat: 45 nm GPDK vs 130 nm sky130 (already framed as a conservative lower bound).

### Tier 1 — MEDIUM effort (do next; convert the discriminating rows)

4. **Dong single-cap auto-zeroed SA (offset, energy)** — sub-block.
   - Build: add a single MIM/MOS cap + offset-sample switch around the existing sky130 StrongARM to form an auto-zero stage; drive from the slope-matched TIA front-end + resistive-MTJ read divider already in the testbench.
   - Output: input-referred σ_off BEFORE vs AFTER single-cap cancellation (the ">60%-class" claim as an own-flow number) + per-decision energy and the area/energy cost of auto-zero → adds **offset and energy axes** for an auto-zero SA in D.2.
   - Reuses: `run_offset_mc.py` MC sweep. Note: SOT-write-line-IR stays N even after repro.

5. **current-sampling SA (offset, energy)** — sub-block.
   - Build: netlist a current-sampling SA (current-mirror/sample front-end + sample cap + latch) in sky130; extract input-referred offset via the same MC mismatch sweep, map to the V_T=23.4 mV window.
   - Output: measured offset-vs-V_T point as a 4th comparator in D.2. Medium (current-mode S/H front end, not a voltage-comparator drop-in).
   - Reuses: `run_offset_mc.py`. No macro needed.

6. **Truong parasitic-adapted write (residual write-V error, P_sw flatness)** — algorithm-on-model + DAC sub-block.
   - Build: per-cell/per-row equivalent wire-R model (`R_{j,i}=ir+(m-j+1)r`) on extracted sky130 sheet-R for an N=256 SOT column; compute pre-distorted resistor-string write-DAC codes; drive into the 776 Ω SOT line in ngspice; measure residual remote-row write-V error and, via the calibrated P_sw sigmoid, per-row P_sw flatness.
   - Output: Truong's accuracy-only/analog claim → a measured **binary-P_sw / residual-write-error** point on the same axis as our design. Adds DAC + rail + energy ledger ourselves.
   - Reuses: `run_write_dac.py` resistor-string DAC + extracted sheet-R + P_sw model.

7. **Zhu positional-boost write (residual write-V error)** — algorithm-on-model + DAC sub-block.
   - Build: position-dependent IR-droop model along an N-cell line into the low-R SOT load; implement Zhu's positional voltage-boost as a head-voltage adjustment via the resistor-string write-DAC; measure residual remote-row delivered-write-V before/after.
   - Output: a second quantitative point on the **residual-write-error axis** alongside ours and Truong.
   - Reuses: same write-DAC + droop model as #6. (Per-row pre-distortion must be added on top of the paper's global boost.)

8. **Chen–Dolecek 1S1R model (per-row BER)** — algorithm-on-model only.
   - Build: position-dependent write-V-attenuation + binary-asymmetric write/read BER channel on extracted sky130 sheet-R (47.96 Ω/sq) and per-row `I_wr*R_par(row)` droop; compare per-row BER map with vs without our IR pre-distortion.
   - Output: algorithm-level per-row BER point (NOT a transistor-level datapoint — the paper has no circuit). Full BCH coding stack is out of scope.
   - Reuses: existing `write_dac_ir` droop model (148 mV / 16.5% droop on N=256).

9. **RRAM XNOR-BNN readout (offset, energy/conversion)** — sub-block.
   - Build: a single 3-bit flash ADC slice (paper's readout converter) + 8-to-1 column mux in sky130; drive with a resistive bitline divider emulating HRS/LRS popcount levels; characterize comparator input-referred offset (MC) vs popcount LSB step and energy/conversion.
   - Output: converts the "shared/amortized ADC + resistive read load" row to a measured **offset/energy** datapoint for a flash digitizer. RRAM/array emulated as resistors.
   - Reuses: comparator + flash building blocks already in the flow (7 comparators + ladder + encoder).

10. **VECOM offset-compensation kernel (margin recovery)** — algorithm-on-model.
    - Build: offset-conductance remap (`G'=G+G00`, subtract `N*I00` via one reference column) on the existing column-readout model; measure decision-margin recovery vs the V_T≈23 mV window under our device-variation distribution.
    - Output: a **read-side margin/energy** point (honestly framed as read-side, not write-IR). The full VECOM macro is infeasible.
    - Reuses: `run_offset_mc.py` SA/readout testbench. (Submodule placement caveat: VECOM is read/encode-side.)

11. **PICO-RAM comparator power-gating (energy-saving %)** — sub-block.
    - Build: a two-comparator front end (extracted StrongARM = Cmp1; near-minimum auto-zeroed Cmp2 at higher Vref gating Cmp1); drive with the existing comparator harness stimulus; measure per-decision energy with/without gating + gated-vs-ungated decision-error rate.
    - Output: a measured 55.8%-class **comparator-amortization energy-saving %**, comparable to our spatial column-sharing axis. The full time-domain VTC+folding-TDC ADC is NOT needed.
    - Reuses: StrongARM/double-tail macros. (Auto-zero/SAZ timing + Vref margin must be tuned.)

12. **Liu–Zhang SAR/SS hybrid (fJ/conv-step)** — sub-block.
    - Build: reuse extracted StrongARM + binary-weighted cap-DAC for the SAR (MSB) phase; add a single-slope LSB phase (ramped resistor-string DAC + counter), comparator shared; make 2–8 b reconfigurable.
    - Output: a measured fJ/conv-step point for a SAR/SS hybrid in D.4. Produces NEW same-flow numbers for comparator energy/offset/split (paper reports none).
    - Reuses: `sar_capdac_tran.py` + comparator. (SS ramp generator + SAR→SS handoff are new.)

13. **image-sensor SAR/SS hybrid (energy)** — sub-block.
    - Build: add the single-slope LSB stage on top of the existing SAR cap-DAC (shared global ramp for lower 6 bits) and transient-measure energy.
    - Output: the two-step SAR/SS hybrid as a measured point; our flow PRODUCES the comparator/cap-DAC split (paper gives none). Explicitly flagged "SS-hybrid not done" in current `comparison_results.json`.
    - Reuses: `sar_capdac_tran.py`. (Largely the same SS extension as #12.)

14. **Yoon sMTJ p-bit driver (V_th trim, P_sw-vs-bias, energy)** — sub-block + algorithm-on-model.
    - Build: NMOS+sMTJ-series divider in sky130 using our calibrated stochastic sMTJ model + 1.8 V rail; implement the VTC (2 PU + 2 PD) + inverter; reproduce the 0.7–1.1 V / 100 mV threshold sweep; sweep DC gate bias to measure time-averaged digital output vs bias (the sigmoid the paper only asserts) against our 23 mV window; optionally extract write energy/op.
    - Output: turns the **V_th-trim** row into a number (achieved vs target threshold, step monotonicity) + a bias-resolution and energy point the paper never gives.
    - Reuses: comparator/DAC cells + stochastic sMTJ model + transient/MC harness. Medium (co-sim of stochastic sMTJ with ngspice).

### Tier 2 — INFEASIBLE (keep qualitative)

- **Xcel-RAM full macro** — custom 10T bitcell array + charge-sharing XNOR-popcount + dual-stage ADC + sectioning; the in-array XNOR-popcount (its distinctive contribution) cannot be reproduced. *Partial only:* the SAR digitizer back-end could be approximated (medium) but would not give a like-for-like 1.914 pJ/op. **Keep row qualitative.**
- **Zhong fully-analogue memristor RC macro** — memristor reservoir dynamics + analog MAC readout on a device stack we do not have; no ADC/comparator/cap-DAC to reproduce. **Keep as a qualitative RC-context anchor only.**

---

## 4. Recommendation — final defensible form of D.5

**Adopt a "corrected matrix + cited justification + targeted quantification" strategy, in this priority order:**

**P0 — Correct the indefensible marks now (zero new simulation).** Apply the eight §2.1 fixes to tables D.4/D.5/D.6 (lines 65–92 of `appendix_D_circuit_comparison.md`): the one hard error (R1, Xcel-RAM silicon ✓→✗) plus seven softenings (R2–R8). Apply the six §2.2 upgrades (U1–U6). This alone makes every cell match what the cited paper actually reports.

**P1 — Make every non-N cell self-defending.** Replace the bare ✓/∼ glyphs with a matrix whose caption (or a companion footnoted list) carries the one-line cited justification from §1 for each non-N cell. Add the §1.4 low-confidence footnotes (`[lo]`) noting those five marks rest on abstract/paywalled evidence. Add one global footnote stating the matrix is qualitative *by design* — papers do not co-report offset + energy at one node/level, so cross-node normalization would distort; quantitative comparison lives only in D.2–D.4.

**P2 — Fix the attribution/over-attribution slips.** In `submodule_survey.json`: relabel "Cassuto 1S1R 2019" → Chen–Dolecek, "Zhang 2024" (PICO-RAM) → Zhiyu Chen; remove/recite the V/2-vs-V/3 attribution to Chen–Dolecek; reframe the Zhong "approach" field from "an ADC quantizes the read currents" to "fully-analogue RC that motivates why digitizing reservoir states is costly."

**P3 — Migrate the low-effort sub-blocks into the quantitative tables (retire matrix rows).** Execute Tier 0 first (Kim, Andrulis, Dutta — two algorithm-on-model + one drop-in comparator), then the highest-value Tier 1 items that *discriminate our design*: **Dong auto-zero SA** and **current-sampling SA** → new offset/energy rows in **D.2**; **Truong** and **Zhu** → residual-write-error / P_sw-flatness rows in **D.3**. Each migrated design moves OUT of the D.5 matrix and INTO D.2–D.4 as a measured point, shrinking the qualitative matrix to only the genuinely infeasible macros. Target after P3: D.5 retains only Xcel-RAM and Zhong (Tier 2) plus any rows not yet reproduced, each with cited justification.

**P4 — Optional polish.** Reproduce the remaining Tier 1 sub-blocks (RRAM flash slice, PICO-RAM gating, Liu–Zhang / image-sensor SS-hybrid, Yoon p-bit) as time allows; each further thins the matrix.

**Net effect:** D.5 stays a matrix (it still usefully maps the design space) but (a) contains no mark a reviewer can refute from the source, (b) carries an inline citation for every non-N cell, (c) honestly flags low-confidence cells, and (d) shrinks over P3/P4 as qualitative rows become measured D.2–D.4 datapoints — converting "we cite that ours is better" into "we measured it in the same flow."
