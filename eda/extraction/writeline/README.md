# `writeline/` — write-line IR-drop (errata R3) + write-energy overhead (R5)

**Track B of the Magic-PEX push (2026-06-26).** The higher-ROI half of the "where do R3/R5 actually
live" question: not inside the readout sense-amp, but in the **column write line** that delivers the
~1.16 mA write current to the selected sMTJ cell.

## Method
1. `gen_writeline_straps.py` (KLayout) — emits known-geometry metal straps (poly/li1/met1/met2/met3,
   each L=200 µm × W=0.5 µm = 400 squares) with a label at each end → `writeline_straps.gds`.
2. `run_extresist.sh` (Magic) — `extract do resistance → extract all → extresist → ext2spice` on the
   straps to read the end-to-end R. **Validation:** extracted poly = **47.96 Ω/sq** vs the sky130A
   techfile `resist` value **48.2 Ω/sq** (0.5 %) — confirms the extresist flow and the sheet-R table.
3. `analyze_ir_drop.py` (pure Python) — scales Magic's techfile sheet R (TT + high corner) to a real
   column write path and compares the parasitic series R / IR-drop / energy to the 776 Ω write device.

sky130 sheet R used (Magic `sky130A.tech`, Ω/sq): li1 12.8 · met1 0.125 · met2 0.125 · met3 0.047 ·
poly 48.2.  Contacts (Ω): mcon 9.3 · via1 4.5 · via2 3.41.

## Model
Calibrated write point: **0.9 V across 776 Ω for 0.75 ns → 0.783 pJ** (I_write = 1.16 mA). The
on-chip path adds **round-trip metal R** (bit line driver→cell + source line cell→sink), each of
length L = N_cells × cell_pitch. Parasitic R_par = 2·Rs·(N·pitch/W), in series with the 776 Ω; the
IR-drop = I_write·R_par and the extra energy = I_write²·R_par·t (both = R_par/776 of the device).
*Assumption (stated):* cell_pitch = 2 µm; honesty: ratios not absolutes, sky130 130 nm pessimistic.

## Results (R3) — `ir_drop_summary.json`
| column N | met2, W=1 µm | R_par | IR-drop | % of 776 Ω |
|---|---|---|---|---|
| 16  | negligible | 8 Ω | 9 mV | 1.0 % |
| 64  | small | 32 Ω | 37 mV | 4.1 % |
| **256** | **significant** | **128 Ω** | **148 mV** | **16.5 %** (19 % hi-corner) |
| 1024 | severe | 512 Ω | 594 mV | 66 % |

At N=256: met3 wide (W=2 µm) cuts it to ~3 %; **li1 is catastrophic (6.5–26 kΩ)** — never route the
write line on li1/poly. End via-stacks add ~28 Ω (3.6 %), reducible by paralleling vias.

## Conclusions
- **R3 (IR-drop):** negligible for small columns (N≤64, <5 %), **significant for tall columns**
  (N≥256 → ~16 % on met1/met2). Design guidance: route the write line on **met2+**, widen it, or
  **segment tall columns**; budget **~10–20 % write headroom** for N≥256.
- **Write-voltage headroom (ties to p_sw):** 148 mV IR-drop on a 0.9 V write means the far cell sees
  only ~0.75 V → it falls below the calibrated 0.8958 V write point, shifting the write-probability
  sigmoid (β_s) → higher write-error at the column's far end unless compensated. A concrete,
  device-aware tall-column limit for the thesis.
- **R5 (end-to-end energy):** add R_par/776 to the write-energy budget (+16.5 % at N=256 met2 on top
  of the 0.783 pJ device write).

## Reproduce
```bash
wsl -d Ubuntu-24.04-EDA -- bash -lc \
  'cd "<repo>/eda/extraction/writeline" && klayout -b -r gen_writeline_straps.py && bash run_extresist.sh'
python eda/extraction/writeline/analyze_ir_drop.py
```
