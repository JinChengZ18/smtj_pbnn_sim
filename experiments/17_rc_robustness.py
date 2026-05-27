"""17 -- Device-variation and noise robustness of the sMTJ reservoir.

Where the PBNN treats device-to-device (D2D) variation as a precision liability
(experiment 08: V_th stability is the dominant accuracy bottleneck), a reservoir
turns the same variation into an asset: a spread of thermal-stability factors
Delta is a spread of relaxation times tau, which raises the effective
dimensionality of the node pool. Four panels:

  (a) memory capacity vs CV(Delta)  -- heterogeneity HELPS
  (b) memory capacity vs CV(V_c0)   -- benign up to large spread
  (c) memory capacity vs read noise, at two input drives -- the real limiter (SNR)
  (d) NARMA-10 NRMSE vs CV(Delta)   -- the benefit holds on a nonlinear task

Reference: the Chapter 2.3 wafer process variation is CV(Delta) = 7.7%; the
panels mark it to show the device sits in the benign-to-beneficial regime.
Panels (a,b,d) use the noise-free mean-field mode to isolate each variation
channel from shot noise.

Run from the repo root:

    python experiments/17_rc_robustness.py
"""

from __future__ import annotations

from pathlib import Path
import sys
import time

import numpy as np
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from smtj_pbnn_sim.reservoir import (                              # noqa: E402
    ReservoirConfig, SMTJReservoir, RidgeReadout, nrmse, memory_capacity)
from smtj_pbnn_sim.reservoir import tasks                         # noqa: E402

PURPLE, RED, DEEP, GREEN, LILAC = "#5E3F8C", "#A82038", "#9580BD", "#1A6B5A", "#C99FD4"
WAFER_CV = 0.077                       # Chapter 2.3 wafer CV(Delta)


def _cfg(**kw):
    # delta_cv=0 baseline so each panel isolates one variation channel.
    base = dict(n_nodes=120, mode="meanfield", effective_spectral_radius=0.6,
                effective_input_scale=0.5, dt=8e-9, delta_cv=0.0, seed=1)
    base.update(kw)
    return ReservoirConfig(**base)


def main() -> None:
    t0 = time.time()
    u = tasks.memory_capacity_inputs(1500, seed=2)
    u_n, y_n = tasks.narma10(2000, seed=3)

    def mc(**kw):
        X = SMTJReservoir(_cfg(**kw), 1).run(u, washout=100)
        return memory_capacity(X, u[100:], max_delay=30)[0]

    def narma(**kw):
        X = SMTJReservoir(_cfg(**kw), 1).run(u_n, washout=200)
        ya = y_n[200:]
        n_tr = 1300
        ro = RidgeReadout(alpha=1e-3).fit(X[:n_tr], ya[:n_tr])
        return nrmse(ya[n_tr:], ro.predict(X[n_tr:]))

    cv_delta = np.array([0.0, 0.05, 0.077, 0.12, 0.2, 0.3, 0.45, 0.6])
    mc_delta = np.array([mc(delta_cv=c) for c in cv_delta])
    narma_delta = np.array([narma(delta_cv=c) for c in cv_delta])

    cv_vc0 = np.array([0.0, 0.05, 0.1, 0.15, 0.25, 0.4, 0.55])
    mc_vc0 = np.array([mc(v_c0_cv=c) for c in cv_vc0])

    read = np.array([0.0, 0.005, 0.01, 0.02, 0.04, 0.08, 0.15])
    mc_rn_lo = np.array([mc(read_noise=r, effective_input_scale=0.5) for r in read])
    mc_rn_hi = np.array([mc(read_noise=r, effective_input_scale=2.0) for r in read])

    print(f"MC at no variation        : {mc_delta[0]:.2f}")
    print(f"MC at wafer CV(Delta)=7.7%: {mc(delta_cv=WAFER_CV):.2f}  (>= baseline => benign)")
    print(f"MC at CV(Delta)=30%       : {mc(delta_cv=0.3):.2f}  (heterogeneity helps)")

    # ----------------------------- figure ---------------------------------#
    fig, ax = plt.subplots(2, 2, figsize=(14, 10))

    ax[0, 0].plot(cv_delta * 100, mc_delta, "o-", color=GREEN, lw=2)
    ax[0, 0].axvline(WAFER_CV * 100, color=RED, ls="--", lw=1.6,
                     label="wafer CV = 7.7%")
    ax[0, 0].set_xlabel(r"device-to-device CV($\Delta$) (%)")
    ax[0, 0].set_ylabel("memory capacity")
    ax[0, 0].set_title("Variation HELPS: heterogeneous $\\tau$ enrich the pool")
    ax[0, 0].legend(fontsize=10)
    ax[0, 0].grid(alpha=0.3)

    ax[0, 1].plot(cv_vc0 * 100, mc_vc0, "o-", color=PURPLE, lw=2)
    ax[0, 1].axvline(WAFER_CV * 100, color=RED, ls="--", lw=1.6)
    ax[0, 1].set_xlabel(r"device-to-device CV($V_{c0}$) (%)")
    ax[0, 1].set_ylabel("memory capacity")
    ax[0, 1].set_title("Benign to $V_{c0}$ spread until devices destabilise")
    ax[0, 1].grid(alpha=0.3)

    ax[1, 0].plot(read, mc_rn_lo, "o-", color=RED, lw=2, label="input drive 0.5")
    ax[1, 0].plot(read, mc_rn_hi, "s-", color=DEEP, lw=2, label="input drive 2.0")
    ax[1, 0].set_xlabel("additive read-noise std (state units)")
    ax[1, 0].set_ylabel("memory capacity")
    ax[1, 0].set_title("Sense noise is the real limiter (SNR-bound)")
    ax[1, 0].legend(fontsize=10)
    ax[1, 0].grid(alpha=0.3)

    ax[1, 1].plot(cv_delta * 100, narma_delta, "o-", color=GREEN, lw=2)
    ax[1, 1].axvline(WAFER_CV * 100, color=RED, ls="--", lw=1.6,
                     label="wafer CV = 7.7%")
    ax[1, 1].set_xlabel(r"device-to-device CV($\Delta$) (%)")
    ax[1, 1].set_ylabel("NARMA-10 NRMSE (lower better)")
    ax[1, 1].set_title("Benefit holds on a nonlinear task")
    ax[1, 1].legend(fontsize=10)
    ax[1, 1].grid(alpha=0.3)

    fig.suptitle("sMTJ reservoir: variation tolerance and the noise limit",
                 fontsize=14, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out = REPO / "figures" / "17_rc_robustness.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(f"\nFigure saved: {out.relative_to(REPO)}")
    print(f"Total runtime: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
