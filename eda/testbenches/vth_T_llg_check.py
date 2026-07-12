"""LLG cross-validation of the V_th(T) chain (T2-2 dual-model anchor).

The analytic chain predicts the switching threshold tracks K_eff(T)
through the 81%-compensated anisotropy: I_th(T)/I_th(300) = keff_ratio(T)
(0.9263 at 330 K, 1.0731 at 270 K). The full LLG stack applies the SAME
Bloch/Callen-Callen material laws internally (time_series_cases scales
Ms/Ki by the instantaneous temperature, thermal field included, ambient +
self-heating), but through the complete dynamics rather than the
Neel-Brown reduction. Honest scope: the temperature DIRECTION is forced
by construction (identical material laws), so the check constrains only
the MAGNITUDE of the propagation through the dynamics -- and at 200
trials the I_50 ratios carry ~1% statistical uncertainty, so the
0.3-0.4% central agreement should be quoted as 'within the ~1% MC
uncertainty', a ~1.7-2 sigma consistency, not a precision match.

Device caveat (stated wherever this is cited): the LLG stack is the
Chapter-2 VGSOT device (Delta ~ 48 kT retention), not the sMTJ variant;
the check anchors the K_eff(T) propagation of the AS-BUILT stack only --
the variant realization (trim vs shrink) changes the compensation ratio
and is bracketed as a scenario band in exp30.

Method: SER vs I_SOT at T_ambient in {270, 300, 330} K, 200 trials/point,
self-heating ON (calibration point), generator RNG; I_50 extracted by
linear interpolation of the SER = 0.5 crossing; compare I_50(T)/I_50(300)
against keff_ratio(T).

Run from the repo root:  python eda/testbenches/vth_T_llg_check.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "eda" / "vendor" / "vgsot-sim" / "src"))

TEMPS = (270.0, 300.0, 330.0)
# widened, finer bracket: chain predicts +-7% threshold motion at +-30 K
I_GRID = tuple(-1e-6 * x for x in
               (1500, 1400, 1300, 1250, 1200, 1150, 1100, 1050, 1000, 950, 850))
TRIALS = 200
SEED = 20260713


def main() -> None:
    from vgsot_sim.configs import SerSotNoVcmaThermalConfig
    from vgsot_sim.ser_cases import ser_sot_no_vcma_thermal
    from smtj_pbnn_sim.device.thermal_scaling import keff_ratio

    out_rows = []
    i50 = {}
    for k, T in enumerate(TEMPS):
        cfg = replace(SerSotNoVcmaThermalConfig(),
                      i_sot_list=list(I_GRID), trials=TRIALS)
        t0 = time.time()
        res = ser_sot_no_vcma_thermal(
            cfg, show_progress=False, enable_self_heating=True,
            T_ambient_K=float(T), seed=SEED + k, rng_mode="generator")
        el = time.time() - t0
        amps = -np.asarray(res.x)          # magnitudes, ascending order check
        ser = np.asarray(res.ser)
        order = np.argsort(amps)
        amps, ser = amps[order], ser[order]
        # SER falls from ~1 (no switch) to ~0 as |I| grows; find 0.5 crossing
        idx = np.where((ser[:-1] >= 0.5) & (ser[1:] < 0.5))[0]
        if len(idx):
            i = idx[-1]
            i_th = float(np.interp(0.5, [ser[i + 1], ser[i]],
                                   [amps[i + 1], amps[i]]))
        else:
            i_th = float("nan")
        i50[T] = i_th
        out_rows.append(dict(T_K=T, i50_uA=i_th * 1e6, elapsed_s=el,
                             ser=ser.tolist(), i_uA=(amps * 1e6).tolist()))
        print(f"T={T:.0f} K: I_50 = {i_th * 1e6:.1f} uA "
              f"({el:.0f} s)", flush=True)

    ref = i50[300.0]
    comparison = {
        f"{T:.0f}K": dict(
            llg_ratio=(i50[T] / ref if np.isfinite(i50[T]) else None),
            chain_keff_ratio=float(keff_ratio(T)))
        for T in TEMPS
    }
    for key, v in comparison.items():
        print(f"{key}: LLG I_50 ratio {v['llg_ratio']:.4f} vs "
              f"chain keff_ratio {v['chain_keff_ratio']:.4f}", flush=True)

    out = dict(trials=TRIALS, seed=SEED, i_grid_uA=[i * 1e6 for i in I_GRID],
               self_heating=True, rows=out_rows, comparison=comparison,
               note="LLG stack = Chapter-2 VGSOT device; validates the "
                    "platform K_eff(T) propagation shared by both variants")
    out_path = Path(__file__).with_name("vth_T_llg_summary.json")
    out_path.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"summary: {out_path}")


if __name__ == "__main__":
    main()
