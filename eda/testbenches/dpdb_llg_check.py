#!/usr/bin/env python3
"""L2c residual: LLG cross-check of the easy-axis field sensitivity dP/dB.

The dipolar-crosstalk certificate (structure_consistency.py) budgets neighbour
stray field with the STATIONARY two-state sensitivity dp/dB = m/(2 kT)
(free-running / RC regime; worst case). The PBNN write regime senses field
differently: the pulse switching probability responds through the shift of the
critical voltage, roughly dV_eq/dB ~ V/(mu0 Hk_eff) and dP/dB = (beta_s/4) *
dV_eq/dB. This script measures dP_sw/dB_z with the vgsot-sim LLG macrospin MC
(ser_sot_no_vcma_thermal, self-heating ON = the calibration point, same as
llg_validate.py) at the calibrated threshold voltage and compares it with both
analytic pictures -- an independent physics check of the field-sensitivity
channel (dual-model anchor).

Field points: h_ex_z = -10 / 0 / +10 Oe (1 Oe = 1000/(4 pi) A/m; 10 Oe = 1 mT
in mu0*H). +z favours the P state (target m_z = +1), so dP/dB_z > 0 expected.

Compute-heavy (TRIALS x 3 macrospin MC transients). Run from the repo root:
  set PYTHONPATH=eda/vendor/vgsot-sim/src && python eda/testbenches/dpdb_llg_check.py
Env knobs: DPDB_TRIALS (default 1500).
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "eda" / "vendor" / "vgsot-sim" / "src"))

R_SOT = 776.0
V_POINT = 0.895783            # calibrated behavioral V_th (P_sw ~ 0.5)
BETA_S = 42.71                # calibrated sigmoid slope (1/V)
TRIALS = int(os.environ.get("DPDB_TRIALS", "1500"))
FIELD_OE = 10.0               # +-10 Oe = +-1 mT (mu0 H)
SEED = 0xD1D0

KB, T_K = 1.380649e-23, 300.0
MU0 = 4e-7 * np.pi
OE_TO_AM = 1000.0 / (4 * np.pi)


def main():
    from vgsot_sim.configs import PhysicalConstantsConfig, SerSotNoVcmaThermalConfig
    from vgsot_sim.ser_cases import ser_sot_no_vcma_thermal

    c = PhysicalConstantsConfig()
    m_moment = c.Ms * c.tf * np.pi * (c.D_elec / 2) ** 2          # A m^2
    dpdB_stat = m_moment / (2 * KB * T_K) * 1e-3                  # per mT

    # pulse-domain analytic band: dP/dB = (beta_s/4) * V / (mu0 * Hk),
    # with Hk between the config FMR-baseline H_k_eff_RT and the
    # compensation-corrected 2 K_eff / (mu0 Ms) (structure_consistency).
    hk_candidates = {"config_H_k_eff_RT": c.H_k_eff_RT}
    try:
        from vgsot_sim.demag import demag_factors
        nx, ny, nz = demag_factors(c)
        k_int = c.Ki / c.tf
        k_shape = 0.5 * MU0 * c.Ms ** 2 * (nz - nx)
        hk_candidates["compensated_2Keff_mu0Ms"] = 2 * (k_int - k_shape) / (MU0 * c.Ms)
    except Exception as e:                                        # noqa: BLE001
        print(f"(demag-based Hk unavailable: {e})")
    dpdB_pulse = {k: BETA_S / 4 * V_POINT / (MU0 * hk) * 1e-3     # per mT
                  for k, hk in hk_candidates.items()}

    i_sot = -(V_POINT / R_SOT)
    fields_oe = (-FIELD_OE, 0.0, +FIELD_OE)
    psw, ci = [], []
    for k, oe in enumerate(fields_oe):
        const = replace(PhysicalConstantsConfig(), h_ex_z=oe * OE_TO_AM)
        cfg = SerSotNoVcmaThermalConfig(i_sot_list=(i_sot,), trials=TRIALS,
                                        constants=const)
        res = ser_sot_no_vcma_thermal(cfg, show_progress=False, seed=SEED + k,
                                      rng_mode="generator",
                                      enable_self_heating=True)
        p = float(np.asarray(res.psw)[0])
        w = 1.96 * np.sqrt(max(p * (1 - p), 1e-9) / TRIALS)
        psw.append(p); ci.append(w)
        print(f"h_ex_z = {oe:+5.1f} Oe ({oe/10:+.1f} mT): "
              f"P_sw = {p:.4f} +- {w:.4f} (95% CI, {TRIALS} trials)")

    b_mt = FIELD_OE / 10.0                                        # 10 Oe = 1 mT
    slope = (psw[2] - psw[0]) / (2 * b_mt)                        # per mT
    slope_ci = np.hypot(ci[2], ci[0]) / (2 * b_mt)

    print(f"\nLLG measured dP_sw/dB_z at V={V_POINT:.3f} V: "
          f"{slope:+.4f} +- {slope_ci:.4f} per mT")
    print(f"analytic stationary (certificate basis, worst case): "
          f"{dpdB_stat:.4f} per mT")
    for k, v in dpdB_pulse.items():
        print(f"analytic pulse-domain via Vc(H), Hk={hk_candidates[k]:.3g} A/m "
              f"({k}): {v:.4f} per mT")

    out = dict(V_point=V_POINT, R_SOT=R_SOT, trials=TRIALS,
               fields_oe=list(fields_oe), psw=psw, ci95=ci,
               dpdB_llg_per_mT=slope, dpdB_llg_ci95=slope_ci,
               dpdB_stationary_per_mT=dpdB_stat,
               dpdB_pulse_analytic_per_mT=dpdB_pulse,
               note=("Certificate (structure_consistency) uses the stationary "
                     "m/2kT sensitivity = free-running/RC regime, the worst "
                     "case; the write regime senses field through the critical-"
                     "voltage shift. LLG measures the pulse regime directly."))
    (HERE / "dpdb_llg_summary.json").write_text(json.dumps(out, indent=1),
                                                encoding="utf-8")
    print(f"summary written: {(HERE / 'dpdb_llg_summary.json').relative_to(REPO)}")


if __name__ == "__main__":
    main()
