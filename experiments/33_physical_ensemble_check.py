"""33 -- Physical-ensemble re-verification of the device-optimization rules.

The Section 5.4 design guidance (optimal barrier plateau Delta ~ 3.5-4.3,
D2D heterogeneity helps) was obtained in the noise-free mean-field mode,
which Section 5.5 itself qualifies as the infinite-ensemble upper bound.
This experiment re-runs the two one-dimensional claim lines in the
physical sampling mode (mode="stochastic", ensemble = 96 devices/node,
the Fig 5.2(f)/5.11 caliber) with 3 sampling seeds, asking one question:
do the OPTIMA move, not do the absolute values drop (they must).

  (i) MC vs Delta at the exp15(c) caliber (dt = 8 ns, sr = 0, input 0.5,
      delta_cv = 0.25, max_delay = 40): mean-field curve vs stochastic
      mean +- spread; report both argmax positions.
 (ii) MC vs CV(Delta) at the exp17(a) caliber (Delta default, sr = 0.6,
      max_delay = 30, delta_cv in {0, 0.077, 0.30}): does the
      heterogeneity benefit survive shot-noise-limited readout?
(iii) benchmark honesty riders (for the mode-caliber footnote): NARMA-10
      NRMSE and Mackey-Glass 1-step NRMSE at the exp17/exp18 calibers in
      BOTH modes, same seeds.

Outputs:
  runs/33_physical_ensemble_<ts>/{mc_vs_delta.csv, mc_vs_cv.csv, benchmarks.csv}
  figures/33_physical_ensemble.png

Run from the repo root:

    python experiments/33_physical_ensemble_check.py
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout, nrmse, memory_capacity)
from smtj_pbnn_sim.reservoir.node import TelegraphParams           # noqa: E402
from smtj_pbnn_sim.reservoir import tasks                          # noqa: E402
from smtj_pbnn_sim.utils.io import make_run_dir                    # noqa: E402

ENSEMBLE = 96
SEEDS = (1, 2, 3)
DELTAS = np.array([2.0, 2.5, 3.0, 3.5, 4.1, 4.5, 4.91, 5.5, 6.0])
CVS = np.array([0.0, 0.077, 0.30])
PURPLE, RED, GREEN, LILAC = "#5E3F8C", "#A82038", "#1A6B5A", "#C99FD4"


def main() -> None:
    t0 = time.time()
    run_dir = make_run_dir("33_physical_ensemble", base=REPO / "runs")
    u_mc = tasks.memory_capacity_inputs(1500, seed=2)
    u_n, y_n = tasks.narma10(2000, seed=3)

    def res15(Delta, mode, seed):
        # exp15(c) caliber
        return SMTJReservoir(ReservoirConfig(
            n_nodes=120, mode=mode, params=TelegraphParams(Delta=float(Delta)),
            effective_spectral_radius=0.0, effective_input_scale=0.5,
            dt=8e-9, delta_cv=0.25, ensemble=ENSEMBLE, seed=seed), 1)

    def res17(mode, seed, **kw):
        # exp17 caliber
        base = dict(n_nodes=120, mode=mode, effective_spectral_radius=0.6,
                    effective_input_scale=0.5, dt=8e-9, delta_cv=0.0,
                    ensemble=ENSEMBLE, seed=seed)
        base.update(kw)
        return SMTJReservoir(ReservoirConfig(**base), 1)

    def mc_of(res, max_delay):
        X = res.run(u_mc, washout=100)
        return memory_capacity(X, u_mc[100:], max_delay=max_delay)[0]

    def narma_of(res):
        X = res.run(u_n, washout=200)
        ya = y_n[200:]
        ro = RidgeReadout(alpha=1e-3).fit(X[:1300], ya[:1300])
        return nrmse(ya[1300:], ro.predict(X[1300:]))

    # ----- (i) MC vs Delta ------------------------------------------------
    rows_d = []
    mf_curve = np.array([mc_of(res15(D, "meanfield", 1), 40) for D in DELTAS])
    st_curves = np.array([[mc_of(res15(D, "stochastic", s), 40)
                           for D in DELTAS] for s in SEEDS])
    st_mean, st_std = st_curves.mean(axis=0), st_curves.std(axis=0)
    for D, mfv, sm, ss in zip(DELTAS, mf_curve, st_mean, st_std):
        rows_d.append({"Delta": D, "mc_meanfield": round(float(mfv), 3),
                       "mc_stoch_mean": round(float(sm), 3),
                       "mc_stoch_std": round(float(ss), 3)})
        print(f"  Delta={D:4.2f}: MF {mfv:5.2f}  ST(E={ENSEMBLE}) "
              f"{sm:5.2f} +/- {ss:4.2f}")
    d_mf = float(DELTAS[np.argmax(mf_curve)])
    d_st = float(DELTAS[np.argmax(st_mean)])
    print(f"argmax: mean-field Delta*={d_mf}, stochastic Delta*={d_st} "
          f"(plateau band from ch5: 3.5-4.3; PBNN device: 4.91)")

    # ----- (ii) MC vs CV(Delta) -------------------------------------------
    rows_cv = []
    for cv in CVS:
        mfv = mc_of(res17("meanfield", 1, delta_cv=float(cv)), 30)
        sts = [mc_of(res17("stochastic", s, delta_cv=float(cv)), 30)
               for s in SEEDS]
        rows_cv.append({"cv_delta": cv, "mc_meanfield": round(float(mfv), 3),
                        "mc_stoch_mean": round(float(np.mean(sts)), 3),
                        "mc_stoch_std": round(float(np.std(sts)), 3)})
        print(f"  CV={cv:5.3f}: MF {mfv:5.2f}  ST {np.mean(sts):5.2f} "
              f"+/- {np.std(sts):4.2f}")

    # ----- (iii) benchmark riders ------------------------------------------
    rows_b = []
    for mode in ("meanfield", "stochastic"):
        ns = [narma_of(res17(mode, s)) for s in (SEEDS if mode == "stochastic"
                                                 else (1,))]
        rows_b.append({"task": "narma10", "mode": mode,
                       "nrmse_mean": round(float(np.mean(ns)), 4),
                       "nrmse_std": round(float(np.std(ns)), 4)})
        print(f"  NARMA-10 {mode}: {np.mean(ns):.3f} +/- {np.std(ns):.3f}")
    mg = tasks.mackey_glass(2600, seed=4)
    mg = (mg - mg.mean()) / mg.std()
    for mode in ("meanfield", "stochastic"):
        vals = []
        for s in (SEEDS if mode == "stochastic" else (1,)):
            res = SMTJReservoir(ReservoirConfig(
                n_nodes=120, mode=mode, effective_spectral_radius=0.6,
                effective_input_scale=0.8, dt=8e-9, ensemble=ENSEMBLE,
                seed=s), 1)
            X = res.run(mg[:-1], washout=200)
            y = mg[1:][200:]
            ro = RidgeReadout(alpha=1e-5).fit(X[:1500], y[:1500])
            vals.append(nrmse(y[1500:], ro.predict(X[1500:])))
        rows_b.append({"task": "mackey_glass_1step", "mode": mode,
                       "nrmse_mean": round(float(np.mean(vals)), 4),
                       "nrmse_std": round(float(np.std(vals)), 4)})
        print(f"  Mackey-Glass 1-step {mode}: {np.mean(vals):.4f} "
              f"+/- {np.std(vals):.4f}")

    for name, rows in [("mc_vs_delta.csv", rows_d), ("mc_vs_cv.csv", rows_cv),
                       ("benchmarks.csv", rows_b)]:
        with open(run_dir / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader(); w.writerows(rows)
    print(f"CSVs written to {run_dir}")

    # ----- figure -----------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.0))

    ax[0].plot(DELTAS, mf_curve, "o-", color=PURPLE, lw=2,
               label="mean-field (upper bound)")
    ax[0].errorbar(DELTAS, st_mean, yerr=st_std, fmt="s-", color=RED, lw=2,
                   capsize=3, label=f"stochastic (E={ENSEMBLE}, 3 seeds)")
    ax[0].axvspan(3.5, 4.3, color=GREEN, alpha=0.12)
    ax[0].axvline(4.91, color="grey", ls="--", lw=1.4)
    ax[0].text(4.91, ax[0].get_ylim()[0] + 0.3, " PBNN device", rotation=90,
               fontsize=9, color="grey", va="bottom")
    ax[0].set_xlabel(r"thermal stability $\Delta$")
    ax[0].set_ylabel("linear memory capacity")
    ax[0].set_title("Optimal-barrier plateau under physical sampling")
    ax[0].legend(fontsize=9); ax[0].grid(alpha=0.3)

    x = np.arange(len(CVS))
    mfv = [r["mc_meanfield"] for r in rows_cv]
    stv = [r["mc_stoch_mean"] for r in rows_cv]
    ste = [r["mc_stoch_std"] for r in rows_cv]
    ax[1].bar(x - 0.17, mfv, width=0.34, color=PURPLE, label="mean-field")
    ax[1].bar(x + 0.17, stv, width=0.34, yerr=ste, capsize=3, color=LILAC,
              label=f"stochastic (E={ENSEMBLE})")
    ax[1].set_xticks(x)
    ax[1].set_xticklabels([f"CV={c:.1%}" for c in CVS])
    ax[1].set_ylabel("linear memory capacity")
    ax[1].set_title("Does D2D heterogeneity still help?")
    ax[1].legend(fontsize=9); ax[1].grid(alpha=0.3, axis="y")
    fig.tight_layout()
    out = REPO / "figures" / "33_physical_ensemble.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
