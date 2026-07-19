"""35 -- SECDED-protected digital baseline for the bit-flip comparison.

The Table 4.5 comparison exposes a bare INT8 FP-NN to uniform bit flips;
deployed digital MRAM ships with ECC, so the fair question is where the
44 pp PBNN advantage stands against a SECDED-protected baseline. SECDED
Hamming(72,64) corrects any single error per 72-bit codeword and detects
(without correcting) double errors, at 12.5% bit overhead.

Because the correction acts before the weights are read, its effect is a
closed-form mapping of the raw per-bit flip rate p to a residual rate

    p_eff(p) = sum_{k>=2} k C(72,k) p^k (1-p)^(72-k) / 72

(uncorrectable words keep their k flipped bits; the possible +1
miscorrection on odd k >= 3 is neglected, which slightly FAVOURS the
digital baseline). The SECDED-protected accuracy at p therefore equals
the measured bare-INT8 accuracy at p_eff -- evaluated by interpolating
the canonical Experiment-09 sweep on its own model instance, so the new
column is exactly like-for-like with the committed FP column.

Outputs:
  runs/35_ecc_baseline_<ts>/ecc_column.csv
  (printed table rows for Table 4.5)

Run from the repo root:

    python experiments/35_ecc_baseline.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from scipy.stats import binom

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.utils.io import make_run_dir   # noqa: E402

CANONICAL = REPO / "runs" / "09_hardware_bitflip_20260502_061419" / "bitflip_sweep.csv"
N_WORD = 72          # Hamming(72,64) codeword length
OVERHEAD = 72 / 64 - 1.0


def p_effective(p: float) -> float:
    """Residual per-bit flip rate after SECDED on 72-bit codewords."""
    if p <= 0.0:
        return 0.0
    k = np.arange(0, N_WORD + 1)
    pmf = binom.pmf(k, N_WORD, p)
    return float(np.sum(k[2:] * pmf[2:]) / N_WORD)


def main() -> None:
    rows = list(csv.DictReader(open(CANONICAL, newline="", encoding="utf-8")))
    p_grid = np.array([float(r["p_flip"]) for r in rows])
    acc_fp = np.array([float(r["fp_8bit"]) for r in rows])

    def acc_at(p_eff: float) -> float:
        """Interpolate the measured bare-INT8 curve at the residual rate."""
        if p_eff <= p_grid[0]:
            return float(acc_fp[0])
        return float(np.interp(p_eff, p_grid, acc_fp))

    run_dir = make_run_dir("35_ecc_baseline", base=REPO / "runs")
    out = []
    print(f"SECDED Hamming(72,64): bit overhead {OVERHEAD*100:.1f}%; "
          f"residual mapping on the canonical exp09 FP curve "
          f"({CANONICAL.parent.name})")
    for p, a_bare in zip(p_grid, acc_fp):
        pe = p_effective(float(p))
        a_ecc = acc_at(pe)
        out.append({"p_flip": p, "p_eff": f"{pe:.3e}",
                    "fp_bare": round(float(a_bare) * 100, 2),
                    "fp_secded": round(a_ecc * 100, 2)})
        print(f"  p={p:6.3f}: p_eff={pe:9.3e}  bare {a_bare*100:6.2f}%  "
              f"SECDED {a_ecc*100:6.2f}%")
    with open(run_dir / "ecc_column.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    print(f"CSV written to {run_dir}")

    # where does SECDED stop helping? p at which p_eff > half of p
    ps = np.logspace(-4, -0.5, 200)
    pes = np.array([p_effective(float(p)) for p in ps])
    p_half = float(np.interp(0.5, pes / ps, ps))
    print(f"SECDED loses half its correction (p_eff/p = 0.5) at "
          f"p ~ {p_half:.3f}; at p = 0.1 the mean codeword error count is "
          f"{0.1*N_WORD:.1f} -- correction is saturated")


if __name__ == "__main__":
    main()
