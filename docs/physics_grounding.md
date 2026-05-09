# Physics grounding

Every default constant in the simulator traces back to a specific location in Chapter 2.3. This document is the audit trail; if Chapter 2.3 is updated, follow the table below to keep the simulator in sync.

## Layer-1 (cross-pulse-width) parameters

| Symbol | Default | Source | Notes |
|---|---|---|---|
| τ₀ | 1 ns | §2.3.4 prior | Standard attempt-time prior for thermally activated MTJ switching. |
| Δ (AP→P) | 5.15 | §2.3.4 / Table 2.3-9 | Inverted from V_th(t_w) regression of Device A AP→P. |
| Δ (P→AP) | 4.91 | §2.3.4 / Table 2.3-9 | Inverted from V_th(t_w) regression of Device A P→AP. **Default in the simulator** because P→AP is the cleanest curve. |
| V_c0 (AP→P) | 884 mV | §2.3.4 / Table 2.3-9 | Same source. |
| V_c0 (P→AP) | 857 mV | §2.3.4 / Table 2.3-9 | **Default**. |

## Layer-2 (operating-point Sigmoid) parameters

For the chapter primary reference Device A, P→AP, t_w = 0.75 ns:

| Symbol | Default | Source | Notes |
|---|---|---|---|
| V_th | 894 mV | Table 2.3-3, Table 2.3-9 | 100-shot Sigmoid fit at H_x = 200 Oe. |
| β_s | 44.6 V⁻¹ | same | k = 22.43 mV. |
| V_T | 1/44.6 ≈ 22.4 mV | derived from β_s | Not stored independently. |
| R² | 0.993 | Table 2.3-3 | Clean single-stage transition. |

## NB → Sigmoid bridge

| Quantity | Formula | Value (primary ref) |
|---|---|---|
| β_NB analytic | $2 \ln 2 \cdot \Delta / V_{c0}$ | 7.94 V⁻¹ |
| β_NB fit (logistic on NB curve) | numerical fit | ~9.5 V⁻¹ (CV=0 single-device) |
| η_c = β_s_meas / β_NB_fit | empirical | 5.34 (Chapter 2.3 §2.3.5 reports MC value; analytic ratio is 44.6 / 7.94 ≈ 5.62) |

The simulator default is `eta_c = 5.34` to match the chapter MC-derived value. Both numbers are valid depending on whether you treat `β_NB_analytic` or `β_NB_fit` as the reference.

## D2D variation parameters

From Chapter 2.3 §2.3.6 (Brinkman decomposition of PDK mismatch):

| Source | CV contribution | Source |
|---|---|---|
| Geometric volume V_mag | 6.3 % (66 % of CV²) | PDK R_P → Brinkman |
| Interface anisotropy H_k | 4.0 % (27 %) | PDK TMR proxy |
| Saturation magnetization M_s | 2.0 % (7 %) | literature |
| Free-layer thickness t_f | 0.3 % (<1 %) | PDK |
| **Total CV(Δ)** | **7.7 %** | combined |

The simulator parameterizes only the total CV(Δ); the breakdown is informational and influences which process improvement direction has the highest leverage (geometry > interface > magnetization).

## Resistance / TMR

| Symbol | Default | Source |
|---|---|---|
| R_P (Device A) | 4.9 kΩ | §2.3.3 hysteresis low-resistance plateau |
| R_AP (Device A) | ~10 kΩ | §2.3.3 hysteresis high-resistance plateau |
| TMR | 100 % (Chapter typical 100–120 %) | Table 2.3-1 |
| R_SOT | 776 Ω | Table 2.3-2 wafer-mean |

## Energy

The single SOT write energy at the chapter operating point:

$$E = V_{wr}^2 / R_{SOT} \cdot t_w = (0.9 \mathrm{V})^2 / 776 \mathrm{\Omega} \cdot 0.75 \mathrm{ns} \approx 0.78 \mathrm{pJ}.$$

Implemented as `MTJResistance.sot_write_energy(V_wr, t_p, R_SOT)` and exposed as `TechParams.e_smtj_write` (a property derived from the `V_wr_nom`, `R_SOT`, and `t_write` fields).

## What's not from Chapter 2.3

The following are **not** grounded in chapter measurements; they are order-of-magnitude defaults for 28 nm CMOS peripherals:

* `e_dac_step = 5 fJ`
* `e_smtj_read = 5 fJ`
* `e_count_inc = 0.5 fJ`
* `t_dac_step = 1 ns`, `t_smtj_read = 2 ns`, `t_count_inc = 0.5 ns`
* All `a_*` area numbers

These should be replaced by NeuroSim V1.5 floorplan output for any absolute energy/latency claim. Relative T-scaling of energy and latency is correct as-is.

## How to verify

The unit test suite checks every grounded constant:

* `test_arrhenius.py::test_vth_at_75ns_matches_chapter`
* `test_arrhenius.py::test_analytic_beta_NB_matches_chapter`
* `test_calibration.py::test_primary_reference_matches_chapter`
* `test_calibration.py::test_nb_fit_recovers_chapter_delta_apto_p`
* `test_variation.py::test_delta_mode_mean_beta_matches_joint_prediction`
* `test_tmr.py::test_sot_write_energy_chapter_value`
* `test_ppa.py::test_smtj_write_energy_property_matches_chapter`

If any of these fails after a chapter update, the documented constant above should be revised.
