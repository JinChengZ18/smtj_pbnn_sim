# PPA grounding plan — replacing the simulator's 28 nm placeholders with sky130

Ledger of `src/smtj_pbnn_sim/ppa/tech_params.py` grounding. The PPA estimator started from 28 nm order-of-magnitude constants; as of 2026-06-29 **all energies and all areas are sky130-grounded** (first-order), leaving only the precision refinements below.

## Status (2026-06-29)

| PPA input        | value      | grounding | source |
|------------------|-----------:|-----------|--------|
| `e_smtj_write`   | 0.78 pJ    | **physical** | V_wr²/R_SOT·t_p (Chapter 2.3 op point), `tech_params.e_smtj_write` |
| `e_smtj_read`    | 48 fJ      | **EDA**   | sky130 StrongARM SA extraction (`eda/hero/sa_postlayout.py`, range 23–74 fJ; errata R1) |
| `e_dac_step`     | 34 fJ      | **EDA (est)** | `eda/testbenches/dac_counter_energy.py`: ngspice analog core (~0.6 fJ) + sky130 stdcell-cap decode (~33 fJ) |
| `e_count_inc`    | 19 fJ      | **EDA (est)** | same; ~11-bit accumulator clock toggle — cross-checks the area model below |
| `a_smtj_cell`    | 4.6 µm²    | **EDA (est)** | `eda/testbenches/area_estimate.py`: 2T cell, write FET W~2.2 µm @ 1.16 mA dominates |
| `a_sot_track`    | 0.03 µm²   | **EDA (est)** | same; BEOL SOT channel under the MTJ (~negligible planar) |
| `a_dac`          | 800 µm²    | **EDA (est)** | same; 6-bit R-string: 64 unit-R + 63-switch tap MUX (`sky130_fd_sc_hd` cell areas) |
| `a_counter`      | 630 µm²    | **EDA (est)** | same; 11-bit column accumulator w·(DFF+FA), real `sky130_fd_sc_hd` cell areas |

## What was done

**Energies** (`eda/testbenches/dac_counter_energy.py`): grounded the DAC code-set (~34 fJ) and counter increment (~19 fJ) from a sky130 ngspice analog core + gate-capacitance estimate. Net per-MAC breakdown: write ~89 %, read ~5.4 %, DAC ~3.8 %, counter ~2.1 % (peripheral share rose ~1 % → ~11 % vs the old placeholders).

**Areas** (`eda/testbenches/area_estimate.py`): grounded the four area constants from REAL `sky130_fd_sc_hd` standard-cell areas (`.lef` SIZE, row height 2.72 µm: DFF/FA 20.0 µm², MUX2 11.3, einvp 6.3, inv 3.8) plus sky130 design rules. Key result: the **2T cell jumps 0.05 → ~4.6 µm²** because the write-access FET must pass I_wr = V_wr/R_SOT ≈ 1.16 mA (→ W ≈ 2.2 µm at sky130's ~0.52 mA/µm) — the low-R SOT write line drives the cell size. The tile area rises ~70 k → ~670 k µm² (0.07 → 0.67 mm² for 256×256), and the periphery (DAC + counter accumulators) becomes comparable to the array rather than negligible (`figures/04_ppa_breakdown.png`).

## Environment note (corrected 2026-06-29)

An earlier note here claimed the WSL image lacked `sky130_fd_sc_hd`; **that was wrong** — a bad `find /` (errored on a WSL networking warning, `PDK_ROOT` unset) missed it. The library is present at `/opt/pdk/sky130A/libs.ref/sky130_fd_sc_hd/` with both `.lef` (areas, used above) and `.lib` (Liberty). `export PDK_ROOT=/opt/pdk PDK=sky130A` to use it.

## Remaining refinements (precision, not blockers)

1. **DRC-clean GDS extraction of the areas.** The current numbers are cell-count + sized-FET estimates, not laid-out + extracted. To tighten: lay out the 2T cell (Magic/KLayout — the StrongARM under `eda/hero/layout/` is the template; the MTJ stays an abstract BEOL black-box, no sky130 device), the R-string DAC from analog PCells, and a counter from `sky130_fd_sc_hd` placed cells; read the GDS bbox. The softest current assumptions are the unit-resistor area (`A_RUNIT`) and the 1/UTIL routing overhead.
2. **Liberty/OpenSTA energy.** `e_dac_step`/`e_count_inc` are ~2× cap-estimates; the now-confirmed `.lib` lets OpenSTA report characterized switching energy for the decode/accumulator cells. (Hand-parsing Liberty `internal_power` is unit-error-prone — use a tool.)
3. Re-run `experiments/04_ppa_breakdown.py` after any refinement; write grounded values back to `eda/extraction/peripheral_energy.yaml` + `tech_params.py`.

The first-order estimates are flagged as such in `tech_params` and chapter04 §4.6 — they are sky130-grounded, not DRC-extracted.
