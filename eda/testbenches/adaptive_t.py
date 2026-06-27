#!/usr/bin/env python3
"""B8 (plan 3.4): adaptive-T confidence early-exit over the p-bit Bernoulli samples.

The PBNN averages T stochastic p-bit reads per decision (each read = one stochastic SOT write,
the 98.7%-dominant energy). Fixed T spends the SAME T on EASY and HARD inputs. A confidence
early-exit (sequential test) stops as soon as the running estimate is decisively on one side.
The HONEST question is not "adaptive vs fixed-T_max" (different accuracy) but the FRONTIER:
at a matched error, how many AVG samples does adaptive need vs fixed? (the Wald/SPRT advantage).

Model: decisions with true p = sigmoid(z), z ~ N(0, sigma_z) (realistic easy/hard mix).
Truth = sign(p-0.5). Bernoulli(p) samples up to T_max.
  - fixed-T(t)  : majority over first t samples -> err_fixed(t) curve.
  - adaptive(z) : after >=T_min, STOP when |p_hat-0.5| > z*sqrt(p_hat(1-p_hat)/t), else T_max.
For each adaptive point (E[T], err_adapt) we find the fixed-T giving the SAME err (interp the
fixed curve) -> T_iso; the iso-accuracy saving = 1 - E[T]/T_iso. Honesty: synthetic margins;
the saving RATIO + the frontier-left-shift are the transferable claims.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RNG = np.random.default_rng(20260627)
N_DEC = 60000
SIGMA_Z = 2.2
T_MIN = 3
T_MAX = 64


def main():
    z = RNG.normal(0.0, SIGMA_Z, N_DEC)
    p = 1.0 / (1.0 + np.exp(-z))
    truth = (p >= 0.5)
    draws = (RNG.random((N_DEC, T_MAX)) < p[:, None])
    csum = np.cumsum(draws, axis=1)
    t_idx = np.arange(1, T_MAX + 1)
    phat = csum / t_idx[None, :]

    # fixed-T accuracy curve: err vs t (majority over first t)
    err_fixed_curve = np.array([float(np.mean((phat[:, t - 1] >= 0.5) != truth)) for t in t_idx])

    def fixed_T_for_err(e):
        """Smallest fixed-T whose err <= e (interp); = the iso-accuracy fixed baseline."""
        below = np.where(err_fixed_curve <= e)[0]
        if not len(below):
            return float(T_MAX)
        return float(t_idx[below[0]])

    se = np.sqrt(np.clip(phat * (1 - phat), 1e-9, None) / t_idx[None, :])
    confident = np.abs(phat - 0.5) > (se * 0)  # placeholder, set per z below

    print("=" * 92)
    print("B8 adaptive-T early-exit  (T_min=%d, T_max=%d, N=%d, sigma_z=%.1f)" %
          (T_MIN, T_MAX, N_DEC, SIGMA_Z))
    print("fixed-T curve: err(T=4)=%.4f  err(T=16)=%.4f  err(T=64)=%.4f" %
          (err_fixed_curve[3], err_fixed_curve[15], err_fixed_curve[63]))
    print("=" * 92)
    print(" z_conf  E[T]   err_adapt   T_iso(fixed@same err)   iso-saving   early%")
    rows = []
    for zc in (1.64, 2.0, 2.33, 2.58, 3.0, 3.5):
        conf = np.abs(phat - 0.5) > zc * se
        conf[:, :T_MIN - 1] = False
        first = np.argmax(conf, axis=1)
        stopped = conf[np.arange(N_DEC), first]
        t_stop = np.where(stopped, first + 1, T_MAX)
        dec = (phat[np.arange(N_DEC), t_stop - 1] >= 0.5)
        err_a = float(np.mean(dec != truth))
        et = float(np.mean(t_stop))
        t_iso = fixed_T_for_err(err_a)
        saving = 1 - et / t_iso
        early = float(np.mean(t_stop < T_MAX))
        print("  %.2f   %5.1f    %.4f         %4.0f                %+5.1f%%      %4.0f%%" %
              (zc, et, err_a, t_iso, saving * 100, early * 100))
        rows.append(dict(z_conf=zc, ET=et, err_adapt=err_a, T_iso=t_iso,
                         iso_saving=saving, frac_early=early))

    best = max(rows, key=lambda r: r["iso_saving"])
    concl = ("B8 result: at MATCHED error, the confidence early-exit needs E[T]=%.1f samples where a "
             "fixed schedule needs T=%.0f -> **%.0f%% fewer stochastic writes at iso-accuracy** "
             "(z_conf=%.2f, err=%.4f). The Wald/SPRT left-shift comes from spending samples only on "
             "the near-p=0.5 tail; easy inputs stop in ~T_min. Since the stochastic write is the "
             "98.7%%-dominant energy, the per-decision saving passes ~1:1 to system write energy. "
             "=> the Exp.06 T-sweet-spot is realizable as a cheap per-decision sequential controller "
             "(B8). Honesty: synthetic margin mix (sigma_z=%.1f); the saving RATIO + the frontier "
             "left-shift transfer, the absolute error depends on the task's margin distribution."
             % (best["ET"], best["T_iso"], best["iso_saving"] * 100, best["z_conf"],
                best["err_adapt"], SIGMA_Z))
    print("\n" + "=" * 92 + "\n" + concl + "\n" + "=" * 92)
    out = dict(T_min=T_MIN, T_max=T_MAX, n_dec=N_DEC, sigma_z=SIGMA_Z,
               err_fixed_curve=[round(float(x), 4) for x in err_fixed_curve],
               sweep=rows, operating_point=best, conclusion=concl)
    (HERE / "adaptive_t_summary.json").write_text(json.dumps(out, indent=2))
    print("wrote adaptive_t_summary.json")


if __name__ == "__main__":
    main()
