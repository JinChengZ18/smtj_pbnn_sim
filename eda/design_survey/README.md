# Submodule design-space comparison — data provenance & reproduction

This directory backs the same-flow quantitative comparison in panel (c) of the readout sense-amplifier, write-driver/DAC and column-shared SAR figures (chapters 4–5). `submodule_survey.json` is the raw multi-agent literature survey; this note records where every number comes from and how to reproduce it.

## Integrity status (2026-06-30, reproduction programme completed 2026-07-01)

Panel (c) of each figure is now the **same-flow quantitative comparison** (ours vs the reproduced alternatives, measured in the identical sky130/ngspice flow), aggregated by `comparison_driver.py` → `comparison_results.json` and plotted by `plot_comparison.py`. It contains **no fabricated coordinates**. The earlier scatter plots were retired because a web-verification pass found that most literature axis values in `submodule_survey.json` were survey ESTIMATES, not numbers reported by the cited papers (back-of-envelope, placeholders, "not reported", and in one case a value copied from our own design); those JSON coordinates are kept only as the raw survey record (the `_caveat` / `_verification` fields). As an interim the panels showed a qualitative capability matrix; with Phase ③ (local reproduction) now complete, that matrix has moved to **appendix D** (`article/appendix_D_circuit_comparison.md`, as markdown tables) and the panels carry the measured comparison.

All ~19 cited papers were confirmed to exist (no hallucinated papers). Citations corrected after verification: PICO-RAM author B. Zhang → **Z. Chen** (IEEE JSSC 2025); ADC-energy model Krishnan/Cao → **Andrulis et al. (MIT)**; image-sensor Kim/Hong/Kwon → **Zhang/Yu/Lyu/Li** (IEICE E101.A:434–437, 2018); 1S1R Cassuto/Ben-Hur → **Chen & Dolecek**; Liu/Zhang add AICAS 2023 DOI; Dutta is a sole author; Yoon author **Caçoilo** (chapter footnote fixed). The appendix-D capability-matrix marks are derived from those (verified) paper descriptions.

### Why the comparison is same-flow reproduction, not a literature scatter

The `verified_reported` block in `submodule_survey.json` records, per design, the metric each paper genuinely reports (value, axis, node). The decisive finding: **almost no design reports both comparison axes at a comparable node/level** — e.g. the double-tail comparator reports an offset (6.9 mV, simulated) but not a per-decision energy; Xcel-RAM reports 1.914 pJ/op but no offset; the SAR papers report a whole-converter FoM or only relative gains. A *legitimate* 2-axis literature scatter therefore **cannot** be built from reported numbers without mixing axes/nodes. Rather than plot an "as-reported" scatter that implies a like-for-like comparison the sources do not support, the comparable designs were re-implemented locally in the same sky130/ngspice flow (Phase ③); the resulting apples-to-apples numbers are in `comparison_results.json` and panel (c).

## Our data points — EDA-derived, reproducible

Every "ours" number (used in the capability matrix, in panels (a)/(b), and in the chapter §4.6 / §5.5 prose) is produced by a committed script and stored in a committed JSON. The circuit design source (Xschem `.sch` + symbols, SPICE netlists, the Verilog-A device model, extraction scripts) is committed under `eda/hero/schematics/`, `eda/hero/*.spice`, `eda/models/smtj_sot.va`, and `eda/extraction/`.

| Our number | Value | Script | Output JSON |
|---|---|---|---|
| Readout SA input-referred offset | 0.39 V_T (9.21 mV / 23.4 mV, N=120 MC) | `eda/hero/run_offset_mc.py` | `eda/hero/offset_mc_summary.json` |
| Readout SA decision energy | ~48 fJ (post-layout 23–74 fJ) | `eda/hero/sa_postlayout.py` | `eda/hero/sa_postlayout_summary.json` |
| Offset-cancellation Pareto / auto-zero (0.064 V_T) | plain SA Pareto-optimal at V_in≥0.5 V | `eda/hero/pareto_offset_cancellation.py` | `eda/hero/pareto_offset_cancellation_summary.json` |
| Readout TIA mapping (offset → ~2.5 popcount) | R_TI=613 Ω @ F=1024 | `eda/hero/readout_mapping.py` | `eda/hero/readout_mapping_summary.json` |
| Write-path residual remote-row error | ~12 mV (N=256, IR pre-distortion) | `eda/hero/ir_aware_writedac.py` | `eda/hero/ir_aware_writedac_summary.json` |
| Write-line IR drop | ~16.5% of R_SOT @ N=256 (met2) | `eda/extraction/writeline/run_extresist.sh` | `eda/extraction/writeline/ir_drop_summary.json` |
| Write-DAC topology choice (R-string; current-steering INL ~1.7 LSB) | resistor-string, 6–7 bit | `eda/hero/write_dac_trim.py` | `eda/hero/write_dac_summary.json` |
| SAR cap-DAC switching energy (transient; supersedes the analytic `sar_capdac_energy.py`) | b=8: conv 394.7 / mono 92.3 fJ (regenerated 2026-07-01) | `eda/testbenches/sar_capdac_tran.py` | `eda/testbenches/sar_capdac_tran_summary.json` |
| Device dual-model agreement (behavioral vs LLG) | ΔV_th ≈ 9.4 mV (0.40 V_T; threshold PASS, slope gap = single-macrospin vs C2C-narrowed slope) | `eda/testbenches/llg_validate.py` | `eda/testbenches/llg_validate_summary.json` |

Pure-Python scripts (`pareto_offset_cancellation.py`, `ir_aware_writedac.py`, `readout_mapping.py`, `write_dac_trim.py`) run with the repo's Python directly. The extraction/transistor-level ones (`sa_postlayout.py`, `run_extresist.sh`, `sar_capdac_energy.py`, `llg_validate.py`) need the open-source sky130 + ngspice/Magic environment described in [`../README.md`](../README.md) and [`../hero/layout/README.md`](../hero/layout/README.md).

## Reproduced literature designs — same-flow scripts & results

Every literature design compared quantitatively in appendix D was re-implemented and measured in the same flow. Each row is one committed script whose output JSON carries the numbers quoted in the appendix (assumptions and integrity caveats are recorded inside each JSON):

| Design (lineage) | What is measured | Script | Output JSON |
|---|---|---|---|
| double-tail comparator (Zhang 2022) | offset 0.393 V_T (N=120) | `eda/hero/run_offset_mc.py --design double_tail` | `eda/hero/offset_mc_double_tail.json` |
| DSA two-stage comparator | offset 0.386 V_T (N=120) | `eda/hero/run_offset_mc.py --design dsa` | `eda/hero/offset_mc_dsa.json` |
| current-sampling SA (Chang 2013) | offset 0.391 V_T (N=120) | `eda/hero/run_offset_mc.py --design current_sampling` | `eda/hero/offset_mc_current_sampling.json` |
| single-cap auto-zero SA (Dong 2018) | offset 0.167 V_T (N=120) | `eda/hero/run_offset_mc.py --design dong_autozero` | `eda/hero/offset_mc_dong_autozero.json` |
| binary current-steering write-DAC | non-monotonic, INL 1.71 LSB | `eda/hero/run_write_dac.py` | `eda/hero/write_dac_current_steering.json` |
| R-2R write-DAC | non-monotonic, INL 2.62 LSB | `eda/hero/run_write_dac.py` | `eda/hero/write_dac_r2r.json` |
| Truong per-row pre-distortion (2019) | parity at DAC quantization floor | `eda/design_survey/repro/truong_predistort.py` | `repro/truong_predistort_summary.json` |
| Zhu global voltage boost (2020) | P_sw residual floors at ~0.10 | `eda/design_survey/repro/zhu_boost.py` | `repro/zhu_boost_summary.json` |
| SAR/SS two-step hybrid (Liu 2023 / Zhang 2018) | avg-case (6,2) wins only at M≥4 sharing | `eda/testbenches/sar_ss_hybrid.py` | `eda/testbenches/sar_ss_hybrid_summary.json` |
| Kim water-filling write energy (2021) | lever = 4^b bit significance → exactly 1.0× on equi-significant p-bits | `eda/design_survey/repro/kim_waterfilling.py` | `repro/kim_waterfilling_summary.json` |
| Andrulis ADC energy law (2024) | our points 1/29–1/50 of the full-ADC bound (one-sided check) | `eda/design_survey/repro/andrulis_adc_model.py` | `repro/andrulis_adc_model_summary.json` |
| RRAM flash-ADC slice (Yin 2020) | pooled edge offset 0.418 V_T (N=40); 2^b−1 vs b comparator energy; 1.8 pJ ladder floor | `eda/design_survey/repro/rram_flash_slice.py` | `repro/rram_flash_slice_summary.json` |
| PICO-RAM comparator gating (Z. Chen 2025) | 24–36% primitive saving (ensemble-dependent) | `eda/design_survey/repro/picoram_gating.py` | `repro/picoram_gating_summary.json` |
| Yoon sMTJ p-bit driver (Caçoilo 2026) | VTC trim: 5 codes, mean step 88 mV = 3.75 V_T | `eda/design_survey/repro/yoon_pbit_driver.py` | `repro/yoon_pbit_driver_summary.json` |

The comparator/DAC/SAR rows run in WSL (`Ubuntu-24.04-EDA`, ngspice + sky130A); the model-level rows (`kim_waterfilling.py`, `andrulis_adc_model.py`) run with the repo's Python directly. Schematics of the reproduced circuits are generated by `eda/hero/schematics/gen_*_sch.py` and published as `article/figs/AppendixD_01..11`.

## Regenerating the figures

```
python eda/gen_supplement_figs.py     # writes letter-free panels to figures/panels/
python eda/build_ppt_figs.py          # composes panels into the chapter decks, exports article/figs/
```

The qualitative capability matrix now lives in appendix D (`article/appendix_D_circuit_comparison.md`) as markdown tables; the quantitative panel (c) is regenerated by `plot_comparison.py` from `comparison_results.json` (run `comparison_driver.py` first). To change a capability verdict, edit the appendix table and keep the corresponding citation/justification in `submodule_survey.json` consistent.
