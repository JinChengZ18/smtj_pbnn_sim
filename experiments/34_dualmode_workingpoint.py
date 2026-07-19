"""34 -- Dual-mode working point: RC on the PBNN device (Delta = 4.91).

Figure 5.10 presents one physical array time-multiplexing probabilistic
inference and reservoir processing, yet Section 5.4 places the RC optimum
at Delta ~ 4.1 (plateau 3.5-4.3) while the PBNN write device is calibrated
at Delta = 4.91. This experiment closes that loop with the timescale-
matching law from Section 5.4(b): the barrier only sets the relaxation
time tau(0) = tau_0 e^Delta / 2, so running the RC phase on the Delta =
4.91 device at a SLOWER task clock dt* ~ tau/2.3 should recover the
plateau capacity -- trading throughput, not capacity.

Measured here (exp15(c) caliber: sr = 0, input 0.5, delta_cv = 0.25,
max_delay = 40):

  * MC vs task step dt at Delta = 4.91, mean-field curve plus the
    physical stochastic check (E = 96, 3 seeds) at the matched point;
  * the recovered fraction of the Delta = 4.1 / dt = 8 ns design-point
    capacity, and the price: clock slowdown factor dt*/8 ns (latency;
    the standby bias dissipation per step scales with dt while the
    per-sample readout energy is unchanged).

Outputs:
  runs/34_dualmode_<ts>/mc_vs_dt.csv
  figures/34_dualmode_workingpoint.png

Run from the repo root:

    python experiments/34_dualmode_workingpoint.py
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
    ReservoirConfig, SMTJReservoir, memory_capacity)
from smtj_pbnn_sim.reservoir.node import TelegraphParams           # noqa: E402
from smtj_pbnn_sim.reservoir import tasks                          # noqa: E402
from smtj_pbnn_sim.device.telegraph import relaxation_time         # noqa: E402
from smtj_pbnn_sim.utils.io import make_run_dir                    # noqa: E402

D_PBNN, D_RC, DT_REF = 4.91, 4.1, 8e-9
DTS = np.array([4, 8, 12, 16, 24, 32, 48, 64, 96, 128]) * 1e-9
ENSEMBLE, SEEDS = 96, (1, 2, 3)
MATCH = 2.3          # tau* ~ MATCH * dt (Section 5.4 timescale-matching law)


def main() -> None:
    t0 = time.time()
    run_dir = make_run_dir("34_dualmode", base=REPO / "runs")
    u = tasks.memory_capacity_inputs(1500, seed=2)

    def mc_of(Delta, dt, mode, seed):
        res = SMTJReservoir(ReservoirConfig(
            n_nodes=120, mode=mode, params=TelegraphParams(Delta=float(Delta)),
            effective_spectral_radius=0.0, effective_input_scale=0.5,
            dt=float(dt), delta_cv=0.25, ensemble=ENSEMBLE, seed=seed), 1)
        X = res.run(u, washout=100)
        return memory_capacity(X, u[100:], max_delay=40)[0]

    mc_ref = mc_of(D_RC, DT_REF, "meanfield", 1)
    tau = float(relaxation_time(0.0, Delta=D_PBNN))
    dt_star = tau / MATCH
    print(f"reference: MC(Delta={D_RC}, dt=8ns, mean-field) = {mc_ref:.2f}")
    print(f"tau(0V, Delta={D_PBNN}) = {tau*1e9:.1f} ns -> matched clock "
          f"dt* = tau/{MATCH} = {dt_star*1e9:.1f} ns "
          f"(slowdown x{dt_star/DT_REF:.1f})")

    rows = []
    mf = np.array([mc_of(D_PBNN, dt, "meanfield", 1) for dt in DTS])
    for dt, v in zip(DTS, mf):
        rows.append({"dt_ns": dt * 1e9, "mc_meanfield": round(float(v), 3),
                     "mc_stoch_mean": "", "mc_stoch_std": ""})
        print(f"  dt={dt*1e9:6.1f} ns: MC(4.91, mean-field) = {v:.2f}")
    i_best = int(np.argmax(mf))
    dt_best = float(DTS[i_best])

    # physical check at the matched point (nearest grid dt to dt*), with the
    # like-for-like stochastic reference at the design point for comparison
    i_star = int(np.argmin(np.abs(DTS - dt_star)))
    sts = [mc_of(D_PBNN, DTS[i_star], "stochastic", s) for s in SEEDS]
    sts_ref = [mc_of(D_RC, DT_REF, "stochastic", s) for s in SEEDS]
    rows[i_star]["mc_stoch_mean"] = round(float(np.mean(sts)), 3)
    rows[i_star]["mc_stoch_std"] = round(float(np.std(sts)), 3)
    print(f"matched point dt={DTS[i_star]*1e9:.0f} ns: "
          f"MC mean-field {mf[i_star]:.2f}, stochastic E={ENSEMBLE} "
          f"{np.mean(sts):.2f} +/- {np.std(sts):.2f} "
          f"(design-point stochastic reference "
          f"{np.mean(sts_ref):.2f} +/- {np.std(sts_ref):.2f})")
    rec = mf[i_star] / mc_ref
    print(f"recovery at matched clock: {rec*100:.0f}% of the Delta={D_RC} "
          f"design point (best grid point: {mf[i_best]:.2f} at "
          f"{dt_best*1e9:.0f} ns = {mf[i_best]/mc_ref*100:.0f}%)")
    print("price: latency x{:.1f}; standby bias dissipation per step scales "
          "with dt, per-sample readout energy unchanged".format(dt_star / DT_REF))

    with open(run_dir / "mc_vs_dt.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"CSV written to {run_dir}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.semilogx(DTS * 1e9, mf, "o-", color="#5E3F8C", lw=2,
                label=r"$\Delta=4.91$ (PBNN device), mean-field")
    ax.errorbar([DTS[i_star] * 1e9], [np.mean(sts)], yerr=[np.std(sts)],
                fmt="s", color="#A82038", ms=9, capsize=4,
                label=f"stochastic, matched clock (E={ENSEMBLE}, 3 seeds)")
    ax.errorbar([DT_REF * 1e9], [np.mean(sts_ref)], yerr=[np.std(sts_ref)],
                fmt="D", color="#1A6B5A", ms=8, capsize=4,
                label=r"stochastic, $\Delta=4.1$ design point")
    ax.axhline(mc_ref, color="#1A6B5A", ls="--", lw=1.6)
    ax.text(DTS[0] * 1e9, mc_ref, r" $\Delta=4.1$, $dt=8$ ns design point",
            fontsize=9, color="#1A6B5A", va="bottom")
    ax.axvline(dt_star * 1e9, color="grey", ls=":", lw=1.4)
    ax.text(dt_star * 1e9, min(mf), r" $dt^*=\tau/2.3$", fontsize=9,
            color="grey", rotation=90, va="bottom")
    ax.set_xlabel("task step dt (ns)")
    ax.set_ylabel("linear memory capacity")
    ax.set_title("RC on the PBNN device: capacity recovered by clock matching")
    ax.legend(fontsize=9, loc="center right")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    out = REPO / "figures" / "34_dualmode_workingpoint.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
