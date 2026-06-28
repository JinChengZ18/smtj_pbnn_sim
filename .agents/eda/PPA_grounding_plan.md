# PPA grounding plan — replacing the simulator's 28 nm placeholders with sky130

Audit + plan for `src/smtj_pbnn_sim/ppa/tech_params.py`. The PPA estimator started from 28 nm order-of-magnitude constants; this is the running ledger of which inputs are grounded in the sky130 EDA flow and which still need work.

## Status (2026-06-29)

| PPA input        | value      | grounding | source |
|------------------|-----------:|-----------|--------|
| `e_smtj_write`   | 0.78 pJ    | **physical** | V_wr²/R_SOT·t_p (Chapter 2.3 op point), `tech_params.e_smtj_write` |
| `e_smtj_read`    | 48 fJ      | **EDA**   | sky130 StrongARM SA extraction (`eda/hero/sa_postlayout.py`, range 23–74 fJ; errata R1) |
| `e_dac_step`     | 34 fJ      | **EDA (energy)** | `eda/testbenches/dac_counter_energy.py`: ngspice analog core (~0.6 fJ) + sky130 stdcell-cap decode (~33 fJ) |
| `e_count_inc`    | 19 fJ      | **EDA (energy)** | `eda/testbenches/dac_counter_energy.py`: ~2 DFF toggles × ~10 fJ (sky130 stdcell-cap) |
| `a_smtj_cell`    | 0.05 µm²   | placeholder | 28 nm order-of-magnitude — **needs sky130 layout** |
| `a_sot_track`    | 0.04 µm²   | placeholder | 28 nm order-of-magnitude — **needs sky130 layout** |
| `a_dac`          | 200 µm²    | placeholder | 28 nm order-of-magnitude — **needs sky130 layout** |
| `a_counter`      | 50 µm²     | placeholder | 28 nm order-of-magnitude — **needs sky130 layout** |

Energies are now all grounded; **the four AREA constants remain placeholders**.

## What was done this round (energies)

`eda/testbenches/dac_counter_energy.py` grounds the two remaining energy placeholders. The DAC analog core (resistor-string + tap transmission-gate + write-driver gate load) is measured with an ngspice transient on the sky130 models; the digital one-hot decode and the counter flip-flops are estimated from sky130 gate capacitance (Cox≈8.6 fF/µm², 1.8 V) because the `sky130_fd_sc_hd` Liberty is not installed in the `Ubuntu-24.04-EDA` image. Net effect on the per-MAC breakdown: peripheral share rises from ~6% to ~11% (DAC 3.8% + read 5.4% + counter 2.1%); the stochastic SOT write still dominates at ~89%.

**Residual uncertainty (~2×)** on `e_dac_step`/`e_count_inc`: the digital terms are cap-estimates, not extracted. Refinement path: install open_pdks `sky130_fd_sc_hd` Liberty and read the DFF/decoder `internal_power`, or synthesize (yosys) + place-route (OpenROAD) the decode+counter and extract.

## Remaining work — area grounding (priority order)

1. **`a_smtj_cell` + `a_sot_track`** (highest leverage — sets the array area, the only block whose area is intrinsic to the device). Artifact: a 1T-1MTJ bit-cell layout (FEOL select FET + BEOL MTJ pillar + SOT channel track) in sky130 (Magic/KLayout), DRC-clean, area read from the GDS bbox; the StrongARM cell layout under `eda/hero/layout/` is a template for the flow. Effort: medium (GUI layout); tool: Magic + sky130A.
2. **`a_dac`** — resistor-string DAC bank floorplan (the chosen 6–7 bit string + tap MUX + driver), area per column. Tool: KLayout/OpenROAD; effort: medium.
3. **`a_counter`** — popcount-counter column pitch. Cheapest once a stdcell flow (yosys + OpenROAD + sky130_fd_sc_hd) is set up; effort: low–medium.

Each grounded value should be written back to `eda/extraction/peripheral_energy.yaml` (the P6 one-way injection interface) and `tech_params.py`, then `experiments/04_ppa_breakdown.py` re-run to refresh `figures/04_ppa_breakdown.png`. The area-extraction work is **GUI/flow-gated** and is deliberately left for a follow-up batch.
