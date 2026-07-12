"""29 -- Echo-state property certification for the telegraph reservoir (T1-4).

The reservoir chapter asserts the echo-state regime but nothing in the
repo verifies it. This experiment derives and validates contraction
criteria for the mean-field update actually implemented in
reservoir/node.py:

    x_i(t) = m_inf(V_i) + (x_i(t-1) - m_inf(V_i)) exp(-k(V_i) dt),
    V_i    = V_bias + (W_in u_t)_i + (W_res x(t-1))_i,

with m_inf(V) = tanh(Delta V / V_c0) and k(V) = 1/tau(V)
= (2 e^-Delta / tau_0) cosh(Delta V / V_c0). The state-to-state Jacobian
(verified against central finite differences to ~3e-9 relative error)
has TWO channels through W_res -- the transfer slope and the
state-dependent decay rate:

    dx_i/dx_j = lam_i delta_ij + W_ij [ (1-lam_i) m_inf'(V_i)
                 + (x_i - m_inf(V_i)) (-dt k'(V_i)) lam_i ].

Three-tier criteria (weakest guarantees explicitly labelled):

  1. SUFFICIENT certificate: row-wise infinity-norm bound with each
     node's actually DRAWN Delta_i and recurrent row norm R_i,
     sup over the reachable voltage interval |V - V_bias| <=
     ||W_in||_inf + rho ||W_res||_inf (401-point grid; integrands are
     smooth and the certified margin dominates the discretisation).
     L < 1 => contraction. Structurally conservative: the slow device
     (high Delta_i) is also the steep one (m' = Delta_i/V_c0), and the
     (1-lam) factor cancels in the slope channel, so the slope channel
     alone would give rho_c ~ V_c0/(Delta_i R_i) independent of dt; the
     k'-decay channel reduces this further (~1.4-2x) and adds a mild dt
     dependence.
  2. Linearised spectral criterion: spectral radius of a Jacobian
     assembled from per-node worst (lam_i, g_i) over a driven-trajectory
     tail. A practical INDICATOR only -- neither an upper nor a lower
     bound on the true Lyapunov exponent (per-node maxima from different
     time steps; sign cancellations in W_res are relied upon).
  3. Twin-trajectory empirical verdict: tail DECAY RATE of the distance
     between trajectories started at x0 = +-1 under one common input
     realisation. A NECESSARY-condition estimate, not ground truth: one
     twin pair can miss coexisting locked attractors (observed here at
     rho = 1.8, V_bias = 0, where the mean-field pair converges but
     common-noise stochastic ensembles freeze at maximal separation).

Stochastic-mode check: COMMON-NOISE twin ensembles (same RNG stream --
telegraph.py:step draws state-independently), convergence measured at
the readout layer (per-node ensemble means, tail-averaged) against a
DECORRELATED baseline (independent noise, otherwise identical). This is
the coupling/common-input convergence notion; an unqualified
"stochastic ESP" would be trivially true and is not claimed.

Outputs: runs/29_esp_cert_<ts>/{phase.csv, phase_dt.csv, summary.json}
         figures/29_esp_certification.png  (letter-free)

Run from the repo root:  python experiments/29_esp_certification.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

DELTA, V_C0, TAU_0 = 4.91, 0.857, 1e-9
DELTA_CV = 0.25              # reservoir D2D heterogeneity (ReservoirConfig)
IN_SCALE = 0.6               # default effective input scale
N_NODES = 100
RHO_GRID = 41
VB_GRID = 41
N_STEPS = 400
RATE_TH = -1e-4              # per-step tail decay-rate threshold
RATE_CAP = -0.05             # sentinel rate when twins coalesce exactly
SEED = 7


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from smtj_pbnn_sim.device.telegraph import TelegraphArray, TelegraphParams
    from smtj_pbnn_sim.reservoir.node import ReservoirConfig, SMTJReservoir
    from smtj_pbnn_sim.utils.io import make_run_dir

    rng = np.random.default_rng(SEED)
    run_dir = make_run_dir("29_esp_cert", base=REPO / "runs")
    plt.rcParams.update({"font.family": "Arial", "font.size": 11})

    # base reservoir at rho_eff = 1 (library-consistent weight draw)
    cfg = ReservoirConfig(n_nodes=N_NODES, effective_spectral_radius=1.0,
                          effective_input_scale=IN_SCALE, mode="meanfield",
                          seed=SEED)
    res = SMTJReservoir(cfg, n_inputs=1)
    W_in = res.W_in.copy()                        # volts
    W_res1 = res.W_res.copy()                     # volts, rho_eff = 1
    win_norm = float(np.abs(W_in).sum(axis=1).max())
    wres1_norm = float(np.abs(W_res1).sum(axis=1).max())
    row1 = np.abs(W_res1).sum(axis=1)             # per-row inf-norms, rho = 1

    def certificate(rho: float, v_bias: float, dt: float) -> float:
        """Row-wise inf-norm sufficient bound; certified iff < 1.

        Node i contributes lam_i + G_i R_i with ITS OWN drawn Delta_i and
        row norm R_i = rho * row1_i, sup over the REACHABLE voltage
        interval (this makes the bound bias-dependent and strictly
        tighter than a global-V sup).
        """
        reach = win_norm + rho * wres1_norm
        V = np.linspace(v_bias - reach, v_bias + reach, 401)[None, :]
        d = np.asarray(res.Delta)[:, None]
        arg = d * V / V_C0
        k = (2.0 * np.exp(-d) / TAU_0) * np.cosh(arg)
        lam = np.exp(-k * dt)
        m_p = (d / V_C0) / np.cosh(arg) ** 2
        k_p = (2.0 * np.exp(-d) / TAU_0) * (d / V_C0) * np.sinh(arg)
        G = (1 - lam) * m_p + 2.0 * lam * dt * np.abs(k_p)
        per_node = (lam + G * (rho * row1)[:, None]).max(axis=1)
        return float(per_node.max())

    def _mf_step(s, u_t, W_res, v_bias, dt):
        V = v_bias + W_in[:, 0] * u_t + W_res @ s
        arg = res.Delta * V / res.V_c0
        k = (2.0 * np.exp(-res.Delta) / TAU_0) * np.cosh(arg)
        m_inf = np.tanh(arg)
        return m_inf + (s - m_inf) * np.exp(-k * dt), V, k, m_inf

    def meanfield_twin(rho: float, v_bias: float, dt: float):
        """Twin trajectories -> (terminal distance, tail decay rate).

        Rate = log-distance slope from the mid-point to the LAST step
        with a strictly positive distance; exact coalescence (float
        identity) maps to the sentinel RATE_CAP -- deeply contracting,
        never 'not contracting' (audit fix: the 1e-300 floor previously
        distorted the rate field and could misclassify coalesced points).
        """
        W_res = rho * W_res1
        u = rng.random(N_STEPS) * 2 - 1
        x = np.ones(N_NODES)
        xp = -np.ones(N_NODES)
        mid = N_STEPS // 2
        d_mid = None
        d_last, t_last = None, None
        for t in range(N_STEPS):
            x, _, _, _ = _mf_step(x, u[t], W_res, v_bias, dt)
            xp, _, _, _ = _mf_step(xp, u[t], W_res, v_bias, dt)
            d_t = float(np.abs(x - xp).max())
            if t == mid - 1:
                d_mid = d_t
            if t >= mid and d_t > 0.0:
                d_last, t_last = d_t, t
        d_end = float(np.abs(x - xp).max())
        if d_mid is None or d_mid <= 0.0 or d_last is None:
            return d_end, RATE_CAP               # coalesced by mid: deep contraction
        rate = (np.log(d_last) - np.log(d_mid)) / max(t_last - (mid - 1), 1)
        if d_end == 0.0:
            rate = min(rate, RATE_CAP)
        return d_end, float(rate)

    def linearized_rho(rho: float, v_bias: float, dt: float) -> float:
        """Practical indicator: spectral radius of a Jacobian assembled
        from per-node worst (lam, g) over a driven-trajectory tail.
        NOT a bound in either direction on the true Lyapunov exponent."""
        W_res = rho * W_res1
        u = rng.random(200) * 2 - 1
        x = np.zeros(N_NODES)
        lam_max = np.zeros(N_NODES)
        g_max = np.zeros(N_NODES)
        for t in range(200):
            x_new, V, k, m_inf = _mf_step(x, u[t], W_res, v_bias, dt)
            if t >= 100:
                arg = res.Delta * V / res.V_c0
                lam = np.exp(-k * dt)
                m_p = (res.Delta / res.V_c0) / np.cosh(arg) ** 2
                k_p = ((2.0 * np.exp(-res.Delta) / TAU_0)
                       * (res.Delta / res.V_c0) * np.sinh(arg))
                g = (1 - lam) * m_p + np.abs(x - m_inf) * dt * np.abs(k_p) * lam
                lam_max = np.maximum(lam_max, lam)
                g_max = np.maximum(g_max, g)
            x = x_new
        J = np.diag(lam_max) + g_max[:, None] * W_res
        return float(np.abs(np.linalg.eigvals(J)).max())

    def stochastic_twin(rho: float, v_bias: float, dt: float,
                        common_noise: bool = True,
                        ensemble: int = 24, substeps: int = 10):
        """Tail-averaged readout-layer distance of twin ensembles.

        common_noise=True  -> same RNG stream (the coupling notion);
        common_noise=False -> independent streams: the DECORRELATED
        baseline the common-noise result is compared against.
        """
        W_res = rho * W_res1
        n_dev = N_NODES * ensemble
        deltas_dev = np.repeat(res.Delta, ensemble)
        a1 = TelegraphArray(n_dev, TelegraphParams(), Delta=deltas_dev,
                            seed=999)
        a2 = TelegraphArray(n_dev, TelegraphParams(), Delta=deltas_dev,
                            seed=999 if common_noise else 1999)
        a1.reset(np.ones(n_dev))
        a2.reset(-np.ones(n_dev))
        u = rng.random(N_STEPS) * 2 - 1
        x1 = np.ones(N_NODES)
        x2 = -np.ones(N_NODES)
        micro = dt / substeps
        tail = []
        for t in range(N_STEPS):
            V1 = v_bias + W_in[:, 0] * u[t] + W_res @ x1
            V2 = v_bias + W_in[:, 0] * u[t] + W_res @ x2
            acc1 = np.zeros(n_dev)
            acc2 = np.zeros(n_dev)
            for _ in range(substeps):
                acc1 += a1.step(np.repeat(V1, ensemble), micro)
                acc2 += a2.step(np.repeat(V2, ensemble), micro)
            x1 = (acc1 / substeps).reshape(N_NODES, ensemble).mean(axis=1)
            x2 = (acc2 / substeps).reshape(N_NODES, ensemble).mean(axis=1)
            if t >= N_STEPS - 50:
                tail.append(float(np.abs(x1 - x2).max()))
        return float(np.mean(tail))

    # ----- (a)+(b): rho x V_bias plane at dt = 8 ns -----------------------
    dt0 = 8.0e-9
    rhos = np.linspace(0.05, 2.0, RHO_GRID)
    vbs = np.linspace(0.0, 0.12, VB_GRID)
    L_map = np.zeros((VB_GRID, RHO_GRID))
    R_map = np.zeros((VB_GRID, RHO_GRID))      # tail decay rate (per step)
    S_map = np.zeros((VB_GRID, RHO_GRID))      # linearised spectral radius
    for i, vb in enumerate(vbs):
        for j, r in enumerate(rhos):
            L_map[i, j] = certificate(r, vb, dt0)
            _, R_map[i, j] = meanfield_twin(r, vb, dt0)
            S_map[i, j] = linearized_rho(r, vb, dt0)
        if (i + 1) % 10 == 0 or i == VB_GRID - 1:
            print(f"V_bias plane: {i + 1}/{VB_GRID} rows")

    # ----- (a2): rho x dt plane at V_bias = 0 -----------------------------
    dts = np.logspace(np.log10(1e-9), np.log10(120e-9), VB_GRID)
    L_dt = np.zeros((VB_GRID, RHO_GRID))
    R_dt = np.zeros((VB_GRID, RHO_GRID))
    S_dt = np.zeros((VB_GRID, RHO_GRID))
    for i, dtv in enumerate(dts):
        for j, r in enumerate(rhos):
            L_dt[i, j] = certificate(r, 0.0, dtv)
            _, R_dt[i, j] = meanfield_twin(r, 0.0, dtv)
            S_dt[i, j] = linearized_rho(r, 0.0, dtv)
        if (i + 1) % 10 == 0 or i == VB_GRID - 1:
            print(f"dt plane: {i + 1}/{VB_GRID} rows")

    # ----- (c): stochastic common-noise subgrid vs decorrelated baseline --
    sto = []
    for r in (0.5, 0.9, 1.4, 1.8):
        for vb in (0.0, 0.06):
            d_cn = stochastic_twin(r, vb, dt0, common_noise=True)
            d_ref = stochastic_twin(r, vb, dt0, common_noise=False)
            i_vb = int(np.argmin(np.abs(vbs - vb)))
            sto.append(dict(rho=r, v_bias=vb,
                            d_common=round(d_cn, 4),
                            d_decorr=round(d_ref, 4),
                            synced=bool(d_cn < 0.25 * d_ref),
                            lin_rho=round(float(np.interp(
                                r, rhos, S_map[i_vb])), 3),
                            mf_rate=round(float(np.interp(
                                r, rhos, R_map[i_vb])), 5)))
            print(f"stochastic twin rho={r:.1f} Vb={vb*1e3:.0f}mV: "
                  f"common {d_cn:.4f} vs decorrelated {d_ref:.4f} "
                  f"-> synced={sto[-1]['synced']}")

    # ----- soundness on BOTH planes ----------------------------------------
    cert_v = L_map < 1.0
    conv_v = R_map < RATE_TH
    lin_v = S_map < 1.0
    cert_d = L_dt < 1.0
    conv_d = R_dt < RATE_TH
    violations = int(np.sum(cert_v & ~conv_v) + np.sum(cert_d & ~conv_d))
    lin_viol = int(np.sum(lin_v & ~conv_v))
    print(f"soundness (both planes): certified-but-not-contracting = "
          f"{violations} (must be 0); vb-plane certified "
          f"{cert_v.mean()*100:.0f}%, linearised-stable "
          f"{lin_v.mean()*100:.0f}%, contracting {conv_v.mean()*100:.0f}%")
    print(f"linearised-criterion optimism: stable-but-not-contracting = "
          f"{lin_viol} points (indicator, not a bound)")

    # ----- figure ----------------------------------------------------------
    rate_levels = np.linspace(-0.05, 0.005, 23)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axes[0]
    cs = ax.contourf(rhos, vbs * 1e3, np.clip(R_map, -0.05, 0.005),
                     levels=rate_levels, cmap="viridis")
    fig.colorbar(cs, ax=ax, label="tail decay rate (per step, mean field)")
    ax.contour(rhos, vbs * 1e3, L_map, levels=[1.0], colors="#A82038",
               linewidths=2)
    ax.contour(rhos, vbs * 1e3, S_map, levels=[1.0], colors="#FFD166",
               linewidths=2)
    ax.contour(rhos, vbs * 1e3, R_map, levels=[RATE_TH], colors="white",
               linewidths=1.6, linestyles="--")
    ax.plot([0.9], [0.0], marker="*", ms=14, color="white",
            mec="black", mew=0.8, clip_on=False)
    ax.plot([0.5], [0.0], marker="o", ms=9, color="white",
            mec="black", mew=0.8, clip_on=False)
    ax.set_xlabel(r"effective spectral radius $\rho_\mathrm{eff}$")
    ax.set_ylabel(r"$V_\mathrm{bias}$ (mV)")
    ax.set_title(f"dt = {dt0*1e9:.0f} ns; red: sufficient, "
                 "yellow: linearised, white: empirical", fontsize=10)

    ax = axes[1]
    cs = ax.contourf(rhos, dts * 1e9, np.clip(R_dt, -0.05, 0.005),
                     levels=rate_levels, cmap="viridis")
    fig.colorbar(cs, ax=ax, label="tail decay rate (per step, mean field)")
    ax.contour(rhos, dts * 1e9, L_dt, levels=[1.0], colors="#A82038",
               linewidths=2)
    ax.contour(rhos, dts * 1e9, S_dt, levels=[1.0], colors="#FFD166",
               linewidths=2)
    ax.contour(rhos, dts * 1e9, R_dt, levels=[RATE_TH], colors="white",
               linewidths=1.6, linestyles="--")
    ax.set_yscale("log")
    ax.plot([0.9], [8.0], marker="*", ms=14, color="white",
            mec="black", mew=0.8)
    ax.plot([0.5], [25.0], marker="o", ms=9, color="white",
            mec="black", mew=0.8)
    ax.set_xlabel(r"effective spectral radius $\rho_\mathrm{eff}$")
    ax.set_ylabel("reservoir step dt (ns)")
    ax.set_title(r"$V_\mathrm{bias}$ = 0; star/circle: operating points",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(REPO / "figures" / "29_esp_certification.png", dpi=300)
    print("figure saved: figures/29_esp_certification.png")

    for name, grid_y, key, Lm, Sm, Rm in (
            ("phase.csv", vbs, "v_bias_V", L_map, S_map, R_map),
            ("phase_dt.csv", dts, "dt_s", L_dt, S_dt, R_dt)):
        with open(run_dir / name, "w", newline="", encoding="utf-8") as fc:
            w = csv.writer(fc)
            w.writerow([key, "rho_eff", "cert_L", "lin_rho", "mf_rate"])
            for i, gy in enumerate(grid_y):
                for j, r in enumerate(rhos):
                    w.writerow([f"{gy:.4g}", round(r, 3),
                                round(Lm[i, j], 4), round(Sm[i, j], 4),
                                f"{Rm[i, j]:.4e}"])

    def op_point(rho, vb, dtv):
        _, rate = meanfield_twin(rho, vb, dtv)
        return dict(L=round(certificate(rho, vb, dtv), 3),
                    lin_rho=round(linearized_rho(rho, vb, dtv), 3),
                    mf_rate=round(rate, 5), contracting=bool(rate < RATE_TH))

    (run_dir / "summary.json").write_text(json.dumps(dict(
        dt_ns=dt0 * 1e9, in_scale=IN_SCALE, delta_cv=DELTA_CV,
        rate_threshold=RATE_TH, rate_cap=RATE_CAP,
        soundness_violations_both_planes=violations,
        linearised_optimism_points=lin_viol,
        cert_fraction_vb_plane=float(cert_v.mean()),
        lin_fraction_vb_plane=float(lin_v.mean()),
        conv_fraction_vb_plane=float(conv_v.mean()),
        op_points={"default(0.9,0,8ns)": op_point(0.9, 0.0, 8e-9),
                   "exp16(0.5,0,25ns)": op_point(0.5, 0.0, 25e-9)},
        stochastic_subgrid=sto,
        note=("tier 1 = row-wise inf-norm SUFFICIENT bound, per-node drawn "
              "Delta_i and row norm, sup over the reachable voltage "
              "interval (bias-dependent); tier 2 = trajectory-linearised "
              "spectral radius, an INDICATOR (bound in neither direction); "
              "tier 3 = twin-trajectory tail decay rate, a NECESSARY-"
              "condition estimate (one pair, one input realisation; can "
              "miss coexisting locked attractors -- see the rho=1.8, "
              "V_bias=0 stochastic freeze); stochastic sync is judged "
              "against the decorrelated baseline")), indent=1),
        encoding="utf-8")
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
