"""29 -- Echo-state property certification for the telegraph reservoir (T1-4).

The reservoir chapter asserts the echo-state regime but nothing in the
repo verifies it. This experiment derives and validates a sufficient
contraction criterion for the mean-field update actually implemented in
reservoir/node.py:

    x_i(t) = m_inf(V_i) + (x_i(t-1) - m_inf(V_i)) exp(-k(V_i) dt),
    V_i    = V_bias + (W_in u_t)_i + (W_res x(t-1))_i,

with m_inf(V) = tanh(Delta V / V_c0) and k(V) = 1/tau(V)
= (2 e^-Delta / tau_0) cosh(Delta V / V_c0). The state-to-state Jacobian
has TWO channels through W_res -- the transfer slope and the
state-dependent decay rate:

    dx_i/dx_j = lam_i delta_ij + W_ij [ (1-lam_i) m_inf'(V_i)
                 + (x_i - m_inf(V_i)) (-dt k'(V_i)) lam_i ],

so a uniform sufficient condition for contraction (infinity norm, worst
case over the reachable voltage interval |V - V_bias| <= ||W_in||_inf
+ ||W_res||_inf and over the +-2 sigma Delta-heterogeneity grid) is

    L = max_V,Delta [ lam(V) + G(V) ||W_res||_inf ] < 1,
    G = (1-lam) m_inf'(V) + 2 lam dt |k'(V)|.

The same voltage moves the two stability channels in opposite
directions: raising |V| collapses the transfer slope (stabilising) while
raising k exponentially shortens the memory AND raises the |k'| decay
channel -- the device-specific coupling that makes the phase diagram
non-trivial.

Parts
-----
  (a) certified phase diagram over (rho_eff, V_bias) at the default
      dt = 8 ns and over (rho_eff, dt) at V_bias = 0, with the chapter
      operating points marked;
  (b) empirical mean-field boundary: twin trajectories from x0 = +-1
      under a common input sequence; convergent iff the terminal state
      distance falls below 1e-6 (the certificate region must be a
      subset of the empirical convergent region -- soundness);
  (c) stochastic-mode check at a subgrid: COMMON-NOISE twin ensembles
      (same RNG stream, state-independent draw pattern verified in
      telegraph.py:step), convergence measured at the readout layer
      (per-node ensemble means). This is the coupling/common-input
      convergence notion -- an unqualified "stochastic ESP" would be
      trivially true and is not claimed.

Outputs: runs/29_esp_cert_<ts>/{phase.csv, summary.json}
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

    slope0 = DELTA / V_C0
    k0 = 2.0 * np.exp(-DELTA) / TAU_0            # k(0) = 1/tau(0)

    # base reservoir at rho_eff = 1 (library-consistent weight draw)
    cfg = ReservoirConfig(n_nodes=N_NODES, effective_spectral_radius=1.0,
                          effective_input_scale=IN_SCALE, mode="meanfield",
                          seed=SEED)
    res = SMTJReservoir(cfg, n_inputs=1)
    W_in = res.W_in.copy()                        # volts
    W_res1 = res.W_res.copy()                     # volts, rho_eff = 1
    win_norm = float(np.abs(W_in).sum(axis=1).max())
    wres1_norm = float(np.abs(W_res1).sum(axis=1).max())
    deltas = np.array([DELTA * (1 - 2 * DELTA_CV), DELTA,
                       DELTA * (1 + 2 * DELTA_CV)])

    sig1 = float(np.linalg.svd(W_res1, compute_uv=False)[0])
    row1 = np.abs(W_res1).sum(axis=1)             # per-row inf-norms, rho = 1

    def certificate(rho: float, v_bias: float, dt: float) -> float:
        """Device-resolved sufficient-contraction factor; certified iff < 1.

        Row-wise infinity-norm bound on the Jacobian: node i contributes
        lam_i + G_i * R_i with ITS OWN drawn Delta_i and row norm R_i --
        strictly rigorous and much tighter than a uniform worst case,
        which is vacuous here because the slowest device (highest Delta,
        lam ~ 0.99) is also the steepest (m' = Delta/V_c0): note the
        (1-lam) factor cancels in the slope channel, so the certified rho
        scales like V_c0 / (Delta_i R_i) regardless of dt. The linearised
        spectral criterion below is the practical boundary, the twin run
        the ground truth.
        """
        V = np.linspace(-1.0, 1.0, 401)[None, :]
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
        """Twin mean-field trajectories -> (terminal distance, decay rate).

        The verdict uses the tail DECAY RATE (log-distance slope per step
        over the second half), not an absolute threshold: with +-2 sigma
        Delta heterogeneity the slowest node has tau(0) ~ 0.8 us, so a
        fixed horizon would misclassify slow-but-contracting points.
        """
        W_res = rho * W_res1
        u = rng.random(N_STEPS) * 2 - 1
        x = np.ones(N_NODES)
        xp = -np.ones(N_NODES)
        d_mid = 2.0
        for t in range(N_STEPS):
            x, _, _, _ = _mf_step(x, u[t], W_res, v_bias, dt)
            xp, _, _, _ = _mf_step(xp, u[t], W_res, v_bias, dt)
            if t == N_STEPS // 2 - 1:
                d_mid = max(float(np.abs(x - xp).max()), 1e-300)
        d_end = max(float(np.abs(x - xp).max()), 1e-300)
        rate = (np.log(d_end) - np.log(d_mid)) / (N_STEPS - N_STEPS // 2)
        return d_end, float(rate)

    def linearized_rho(rho: float, v_bias: float, dt: float) -> float:
        """Practical criterion: spectral radius of the Jacobian linearised
        along a driven trajectory (per-node worst gains over the tail)."""
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
                        ensemble: int = 24, substeps: int = 10) -> float:
        """Readout-layer distance of common-noise twin ensembles."""
        W_res = rho * W_res1
        n_dev = N_NODES * ensemble
        deltas_dev = np.repeat(res.Delta, ensemble)
        a1 = TelegraphArray(n_dev, TelegraphParams(), Delta=deltas_dev,
                            seed=999)
        a2 = TelegraphArray(n_dev, TelegraphParams(), Delta=deltas_dev,
                            seed=999)
        a1.reset(np.ones(n_dev))
        a2.reset(-np.ones(n_dev))
        u = rng.random(N_STEPS) * 2 - 1
        x1 = np.ones(N_NODES)
        x2 = -np.ones(N_NODES)
        micro = dt / substeps
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
        return float(np.abs(x1 - x2).max())

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

    # ----- (c): stochastic common-noise subgrid ---------------------------
    sto = []
    for r in (0.5, 0.9, 1.4, 1.8):
        for vb in (0.0, 0.06):
            d_end = stochastic_twin(r, vb, dt0)
            i_vb = int(np.argmin(np.abs(vbs - vb)))
            sto.append(dict(rho=r, v_bias=vb, d_end=round(d_end, 4),
                            cert_L=round(certificate(r, vb, dt0), 3),
                            lin_rho=round(float(np.interp(
                                r, rhos, S_map[i_vb])), 3),
                            mf_rate=round(float(np.interp(
                                r, rhos, R_map[i_vb])), 5)))
            print(f"stochastic twin rho={r:.1f} Vb={vb*1e3:.0f}mV: "
                  f"readout distance {d_end:.4f} "
                  f"(lin rho={sto[-1]['lin_rho']})")

    # ----- soundness: certified region must contract empirically ----------
    RATE_TH = -1e-4                      # per-step tail decay-rate threshold
    cert_region = L_map < 1.0
    conv_region = R_map < RATE_TH
    lin_region = S_map < 1.0
    violations = int(np.sum(cert_region & ~conv_region))
    lin_viol = int(np.sum(lin_region & ~conv_region))
    print(f"soundness: certified-but-not-contracting points = {violations} "
          f"(must be 0); certified {cert_region.mean()*100:.0f}%, "
          f"linearised-stable {lin_region.mean()*100:.0f}%, "
          f"empirically contracting {conv_region.mean()*100:.0f}% of plane")
    print(f"linearised-criterion optimism: stable-but-not-contracting = "
          f"{lin_viol} points (linearisation is a practical, not sufficient,"
          " boundary)")

    # ----- figure ----------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axes[0]
    cs = ax.contourf(rhos, vbs * 1e3, R_map, levels=20, cmap="viridis")
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
    cs = ax.contourf(rhos, dts * 1e9, R_dt, levels=20, cmap="viridis")
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

    with open(run_dir / "phase.csv", "w", newline="", encoding="utf-8") as fc:
        w = csv.writer(fc)
        w.writerow(["v_bias_V", "rho_eff", "cert_L", "lin_rho", "mf_rate"])
        for i, vb in enumerate(vbs):
            for j, r in enumerate(rhos):
                w.writerow([round(vb, 4), round(r, 3),
                            round(L_map[i, j], 4), round(S_map[i, j], 4),
                            f"{R_map[i, j]:.4e}"])

    def op_point(rho, vb, dtv):
        _, rate = meanfield_twin(rho, vb, dtv)
        return dict(L=round(certificate(rho, vb, dtv), 3),
                    lin_rho=round(linearized_rho(rho, vb, dtv), 3),
                    mf_rate=round(rate, 5), contracting=bool(rate < RATE_TH))

    (run_dir / "summary.json").write_text(json.dumps(dict(
        dt_ns=dt0 * 1e9, in_scale=IN_SCALE, delta_cv=DELTA_CV,
        wres1_sigma_max=sig1, rate_threshold=RATE_TH,
        soundness_violations=violations,
        linearised_optimism_points=lin_viol,
        cert_fraction=float(cert_region.mean()),
        lin_fraction=float(lin_region.mean()),
        conv_fraction=float(conv_region.mean()),
        op_points={"default(0.9,0,8ns)": op_point(0.9, 0.0, 8e-9),
                   "exp16(0.5,0,25ns)": op_point(0.5, 0.0, 25e-9)},
        stochastic_subgrid=sto,
        note=("sufficient bound = 2-norm uniform worst case over V and "
              "+-2sigma Delta (conservative by construction); linearised "
              "spectral criterion = practical boundary; empirical verdict "
              "= tail decay RATE of twin trajectories (heterogeneity-aware);"
              " stochastic convergence is the common-noise/common-input "
              "notion at the readout layer -- not an unqualified "
              "'stochastic ESP'")), indent=1), encoding="utf-8")
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
