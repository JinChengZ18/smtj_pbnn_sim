"""Extract Device A / Device B Psw(V) measurements at t_w = 0.75 ns from the
chapter-2 figure script into a single CSV: data/smtj_psw_curves/measured_0p75ns.csv

This is real measured data (100 cycle repetitions per voltage, H_x = 200 Oe,
SOT-MTJ on 300 mm wafer). Reproduces the DATA dict in sigmoid_fig-V3_0.py.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

# Same DATA dict as in the chapter-2 figure script (sigmoid_fig-V3_0.py).
# Voltages in mV; Psw in [0, 1] from 100-shot averages.
DATA: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {
    ("A", "AP->P"): (
        np.array([800, 820, 840, 860, 880, 900, 920, 940, 960, 980,
                  1000, 1020, 1040, 1060, 1080, 1100], dtype=float),
        np.array([0.000, 0.000, 0.000, 0.000, 0.040, 0.040, 0.580, 0.780,
                  0.720, 0.720, 0.720, 0.860, 0.840, 0.880, 0.900, 1.000])),
    ("A", "P->AP"): (
        np.array([800, 820, 840, 860, 880, 900, 920, 940, 960,
                  980, 1000, 1020], dtype=float),
        np.array([0.000, 0.020, 0.100, 0.180, 0.340, 0.500, 0.820, 0.840,
                  0.900, 0.980, 0.940, 1.000])),
    ("B", "AP->P"): (
        np.array([800, 820, 840, 860, 880, 900, 920, 940, 960], dtype=float),
        np.array([0.000, 0.020, 0.360, 0.380, 0.520, 0.740, 0.740, 0.920, 1.000])),
    ("B", "P->AP"): (
        np.array([840, 860, 880, 900, 920, 940, 960, 980, 1000], dtype=float),
        np.array([0.000, 0.100, 0.180, 0.400, 0.840, 0.960, 1.000, 1.000, 1.000])),
}


def main(out_path: str = "data/smtj_psw_curves/measured_0p75ns.csv") -> None:
    rows = []
    for (dev, direction), (V_mV, P) in DATA.items():
        for v_mV, p in zip(V_mV, P):
            rows.append({
                "device_id": dev,
                "direction": direction,
                "V": float(v_mV) * 1e-3,    # store in volts
                "t_p": 0.75e-9,              # 0.75 ns
                "P_sw": float(p),
                "n_reps": 100,
            })
    df = pd.DataFrame(rows)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
