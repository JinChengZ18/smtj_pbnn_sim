# Submodule design-space comparison — data provenance & reproduction

This directory backs the "vs literature" panel (c) of figures 16, 18 and 5.9 (the readout sense-amplifier, the write-driver/DAC, and the column-shared SAR readout). `submodule_survey.json` is the raw multi-agent literature survey; this note records where every number comes from and how to reproduce it.

## Integrity status (2026-06-30)

The panels are now a **qualitative capability matrix** (Y / partial / N coverage of the task-relevant capabilities), rendered by `CAPS` + `design_cmp_table()` in [`../gen_supplement_figs.py`](../gen_supplement_figs.py). They contain **no fabricated coordinates**. The earlier scatter plots were retired because a web-verification pass found that most literature axis values in `submodule_survey.json` were survey ESTIMATES, not numbers reported by the cited papers (back-of-envelope, placeholders, "not reported", and in one case a value copied from our own design). Those JSON coordinates are kept only as the raw survey record — see the `_caveat` / `_verification` fields at the top of the JSON.

All ~19 cited papers were confirmed to exist (no hallucinated papers). Citations corrected after verification: PICO-RAM author B. Zhang → **Z. Chen** (IEEE JSSC 2025); ADC-energy model Krishnan/Cao → **Andrulis et al. (MIT)**; image-sensor Kim/Hong/Kwon → **Zhang/Yu/Lyu/Li** (IEICE E101.A:434–437, 2018); 1S1R Cassuto/Ben-Hur → **Chen & Dolecek**; Liu/Zhang add AICAS 2023 DOI; Dutta is a sole author; Yoon author **Caçoilo** (chapter footnote fixed). The capability-matrix Y/N/partial marks are derived from those (verified) paper descriptions.

### Phase ② — what the papers actually report (and why there is still no quantitative scatter)

The `verified_reported` block in `submodule_survey.json` records, per design, the metric each paper genuinely reports (value, axis, node). The decisive finding: **almost no design reports both comparison axes at a comparable node/level** — e.g. the double-tail comparator reports an offset (6.9 mV, simulated) but not a per-decision energy; Xcel-RAM reports 1.914 pJ/op but no offset; the SAR papers report a whole-converter FoM or only relative gains. So a *legitimate* 2-axis literature scatter **cannot** be built from reported numbers without mixing axes/nodes. The capability matrix therefore stands as the honest comparison, and a true quantitative (same-axis) comparison is deferred to **Phase ③** (local reproduction of the designs in the same sky130/ngspice flow) — see the revision plan. No "as-reported" scatter is plotted, to avoid implying a like-for-like comparison that the sources do not support.

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
| SAR comparator energy (reuses StrongARM) | ~48 fJ; cap-DAC switching | `eda/testbenches/sar_capdac_energy.py` | `eda/testbenches/sar_capdac_energy_summary.json` |
| Device dual-model agreement (behavioral vs LLG) | ΔV_th ≈ 0.2 mV | `eda/testbenches/llg_validate.py` | `eda/testbenches/llg_validate_summary.json` |

Pure-Python scripts (`pareto_offset_cancellation.py`, `ir_aware_writedac.py`, `readout_mapping.py`, `write_dac_trim.py`) run with the repo's Python directly. The extraction/transistor-level ones (`sa_postlayout.py`, `run_extresist.sh`, `sar_capdac_energy.py`, `llg_validate.py`) need the open-source sky130 + ngspice/Magic environment described in [`../README.md`](../README.md) and [`../hero/layout/README.md`](../hero/layout/README.md).

## Regenerating the figures

```
python eda/gen_supplement_figs.py     # writes letter-free panels to figures/panels/
python eda/build_ppt_figs.py          # composes panels into the chapter decks, exports article/figs/
```

The capability matrix is data-light (Y/N/partial per the table in `gen_supplement_figs.py::CAPS`); to change a verdict, edit `CAPS` and keep the corresponding citation/justification in `submodule_survey.json` consistent.
