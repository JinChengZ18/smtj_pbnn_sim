"""Structure <-> electrical self-consistency and magnetic crosstalk bounds.

Part 1 (retention-Delta closure): predict the RETENTION thermal-stability
factor of the Chapter-2 device geometry from its structural parameter set
(K_i, M_s, t_f, D_elec + exact oblate-spheroid demag) and close the loop
against the publicly reported retention band of the same platform
(Delta ~ 59-64, memory-grade stack). This is deliberately NOT the
Neel-Brown switching-law exponent Delta = 4.91 of the superparamagnetic
variant -- the two are different quantities (retention barrier vs
switching-law exponent; see vgsot-sim docs/parameter_validation.md) and
the comparison table keeps them apart.

Because K_eff = K_i/t_f - 0.5 mu0 Ms^2 (Nz - Nx) sits close to
compensation, the retention Delta is hyper-sensitive to the stack inputs;
the script reports d(Delta)/d(Ki) around the operating point (context for
the calibrated D2D spread CV(Delta) = 7.7%) and inverts the design
window: what diameter (fixed stack) or what K_i trim (fixed diameter)
would deliver the superparamagnetic Delta ~ 4.9.

Part 2 (dipolar crosstalk pitch rule): worst-case neighbour stray-field
coupling of the free layer moment vs array pitch (point dipole + lattice-
sum allowance), converted to a switching-probability shift at the p = 1/2
operating point, with the critical pitch for a 1% shift; plus the generic
field sensitivity dp/dB of the superparamagnetic cell.

Pure Python/numpy (vgsot-sim imported for the geometry/demag code paths).

Outputs:
  eda/testbenches/structure_consistency_summary.json
  figures/structure_consistency.png

Run from the repo root:

    python eda/testbenches/structure_consistency.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "eda" / "vendor" / "vgsot-sim" / "src"))

from vgsot_sim.configs import PhysicalConstantsConfig          # noqa: E402
from vgsot_sim.demag import demag_factors                      # noqa: E402

KB = 1.380649e-23
MU0 = 4e-7 * np.pi
T_K = 300.0
DELTA_SMTJ = 4.91          # NB switching-law exponent (auto-fit, sMTJ variant)
DELTA_PUBLIC = (59.3, 64.0)  # published retention band, memory-grade platform
PITCH_2T = 2.1e-6          # sqrt of the 4.6 um^2 2T cell (write-FET-limited)
DP_BUDGET = 0.01           # crosstalk budget: 1% switching-probability shift


def retention_delta(c: PhysicalConstantsConfig, ki=None, d_elec=None) -> float:
    """Retention barrier E_b/kT from the structural parameter set."""
    ki = c.Ki if ki is None else ki
    if d_elec is not None:
        c = type(c)(**{**c.__dict__, "D_elec": d_elec})
    nx, _, nz = demag_factors(c)
    k_eff = ki / c.tf - 0.5 * MU0 * c.Ms ** 2 * (nz - nx)
    v = c.tf * np.pi * (c.D_elec / 2) ** 2
    return float(k_eff * v / (KB * T_K)), float(k_eff)


def main() -> None:
    c = PhysicalConstantsConfig()
    nx, ny, nz = demag_factors(c)
    d_ret, k_eff = retention_delta(c)
    k_int = c.Ki / c.tf
    k_shape = 0.5 * MU0 * c.Ms ** 2 * (nz - nx)
    print(f"geometry: D_elec={c.D_elec*1e9:.0f} nm, tf={c.tf*1e9:.1f} nm, "
          f"demag (Nx,Nz)=({nx:.4f},{nz:.4f})")
    print(f"K_int = {k_int/1e3:.1f} kJ/m^3, K_shape = {k_shape/1e3:.1f} kJ/m^3 "
          f"-> K_eff = {k_eff/1e3:.1f} kJ/m^3 "
          f"({k_shape/k_int*100:.1f}% compensated)")
    print(f"retention Delta(geometry) = {d_ret:.1f} kT  "
          f"[public platform band {DELTA_PUBLIC[0]}-{DELTA_PUBLIC[1]}; "
          f"NB switching Delta of the sMTJ variant = {DELTA_SMTJ} -- "
          f"a different quantity, kept apart]")

    # near-compensation sensitivity: d(Delta)/(dKi/Ki) in percent-per-percent
    dki = 0.01 * c.Ki
    d_hi, _ = retention_delta(c, ki=c.Ki + dki)
    sens = (d_hi - d_ret) / d_ret / 0.01
    print(f"sensitivity: +1% Ki -> {sens:+.1f}% Delta "
          f"(near-compensation amplification; context for CV(Delta)=7.7%)")

    # design window: reach the superparamagnetic Delta ~ 4.9
    # (a) fixed stack, shrink diameter
    ds = np.linspace(10e-9, c.D_elec, 400)
    d_of_D = np.array([retention_delta(c, d_elec=d)[0] for d in ds])
    d_star = float(np.interp(DELTA_SMTJ, d_of_D, ds))
    # (b) fixed diameter, trim Ki: scan wide enough to bracket the target
    # and ASSERT the root is interior (an earlier 0.9-1.0 scan clamped at
    # the grid edge and silently reported a 10% trim; the true root is
    # ~17%, deepening the compensation to ~0.977)
    kis = np.linspace(0.70, 1.0, 1200) * c.Ki
    d_of_ki = np.array([retention_delta(c, ki=k)[0] for k in kis])
    assert d_of_ki[0] < DELTA_SMTJ < d_of_ki[-1], "trim target not bracketed"
    ki_star = float(np.interp(DELTA_SMTJ, d_of_ki, kis))
    assert kis[0] < ki_star < kis[-1], "trim root clamped at scan edge"
    print(f"design window to Delta={DELTA_SMTJ}: shrink D_elec to "
          f"{d_star*1e9:.1f} nm at fixed stack, or trim Ki by "
          f"{(1-ki_star/c.Ki)*100:.2f}% at fixed D "
          f"(trim deepens the compensation to ~0.98: the sMTJ variant = a "
          f"markedly closer-compensated stack, not a slight tuning)")

    # ----- Part 2: dipolar crosstalk ---------------------------------------
    m = c.Ms * c.tf * np.pi * (c.D_elec / 2) ** 2      # moment [A m^2]
    pitches = np.logspace(np.log10(80e-9), np.log10(4e-6), 200)
    b_nn = MU0 * 2 * m / (4 * np.pi * pitches ** 3)    # on-axis nearest neighbour
    lattice = 1.5                                       # 4 NN + far-ring allowance
    e_kt = m * b_nn * lattice / (KB * T_K)             # worst-case Zeeman asym.
    dp = np.tanh(e_kt / 2.0) / 2.0                     # p-shift at p = 1/2
    pitch_star = float(np.interp(DP_BUDGET, dp[::-1], pitches[::-1]))
    dp_2t = float(np.interp(PITCH_2T, pitches, dp))
    dpdB = m / (2 * KB * T_K)                          # small-signal, p = 1/2
    print(f"moment m = {m:.3e} A m^2; dp/dB = {dpdB*1e-3:.3f} per mT "
          f"({dpdB*1e-4*79.577:.4f} per Oe)")
    print(f"crosstalk: at the 2T pitch {PITCH_2T*1e6:.1f} um dp = {dp_2t:.2e} "
          f"(negligible); dp = 1% critical pitch = {pitch_star*1e9:.0f} nm "
          f"(FET-less dense-BEOL regime only)")

    # drawn-cell backfill (MTJ plan L1): evaluate the certificate at the pitch
    # of the actually drawn 2T cell (eda/hero/layout/cell2t_summary.json,
    # design-bbox short side) -- the drawn cell is looser than the 2.1 um
    # estimate, so the coupling there is smaller still.
    dp_drawn = None
    drawn_pitch = None
    cell_json = REPO / "eda" / "hero" / "layout" / "cell2t_summary.json"
    if cell_json.exists():
        cell = json.loads(cell_json.read_text(encoding="utf-8"))
        if "design_size_um" in cell:
            drawn_pitch = min(cell["design_size_um"]) * 1e-6
            e1 = MU0 * 2 * m / (4 * np.pi * drawn_pitch ** 3) * m * lattice / (KB * T_K)
            dp_drawn = float(np.tanh(e1 / 2.0) / 2.0)
            print(f"drawn-cell backfill: design-bbox short side = "
                  f"{drawn_pitch*1e6:.2f} um -> dp = {dp_drawn:.2e}")

    summary = {
        "geometry": {"D_elec_nm": c.D_elec * 1e9, "tf_nm": c.tf * 1e9,
                     "Nx": nx, "Nz": nz},
        "retention_delta_geometry": round(d_ret, 1),
        "public_platform_band": list(DELTA_PUBLIC),
        "nb_switching_delta_smtj": DELTA_SMTJ,
        "k_int_kJm3": round(k_int / 1e3, 1),
        "k_shape_kJm3": round(k_shape / 1e3, 1),
        "compensation_pct": round(k_shape / k_int * 100, 1),
        "delta_sens_pct_per_pct_Ki": round(sens, 1),
        "design_window": {"D_star_nm": round(d_star * 1e9, 1),
                          "Ki_trim_pct": round((1 - ki_star / c.Ki) * 100, 2)},
        "dipolar": {"moment_Am2": m, "dp_per_mT": dpdB * 1e-3,
                    "dp_at_2T_pitch": dp_2t,
                    "critical_pitch_nm_at_1pct": round(pitch_star * 1e9, 0),
                    "lattice_factor": lattice,
                    "drawn_cell_pitch_um": (round(drawn_pitch * 1e6, 2)
                                            if drawn_pitch else None),
                    "dp_at_drawn_cell_pitch": dp_drawn},
    }
    out_json = Path(__file__).with_name("structure_consistency_summary.json")
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"summary written: {out_json.relative_to(REPO)}")

    # ----- figure -----------------------------------------------------------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 5.0))

    # +/-1% Ki sensitivity envelope and the trimmed-stack curve, from the same
    # forward model (near-compensation amplification made visible)
    d_lo = np.array([retention_delta(c, ki=0.99 * c.Ki, d_elec=d)[0] for d in ds])
    d_hi = np.array([retention_delta(c, ki=1.01 * c.Ki, d_elec=d)[0] for d in ds])
    d_trim = np.array([retention_delta(c, ki=ki_star, d_elec=d)[0] for d in ds])
    trim_pct = (1 - ki_star / c.Ki) * 100
    ax[0].fill_between(ds * 1e9, d_lo, d_hi, color="#5E3F8C", alpha=0.18, lw=0)
    ax[0].plot(ds * 1e9, d_of_D, color="#5E3F8C", lw=2)
    ax[0].plot(ds * 1e9, d_trim, color="#D4A017", lw=1.8, ls="--")
    ax[0].axhspan(*DELTA_PUBLIC, color="#1A6B5A", alpha=0.15)
    ax[0].text(12, np.mean(DELTA_PUBLIC), "published retention band\n"
               "(memory-grade platform)", fontsize=9, color="#1A6B5A",
               va="center")
    ax[0].axhline(DELTA_SMTJ, color="#A82038", ls="--", lw=1.6)
    ax[0].text(44, 1.6, r"NB $\Delta$ = %.2f (superparamagnetic)" % DELTA_SMTJ,
               fontsize=9, color="#A82038")
    ax[0].plot([c.D_elec * 1e9], [d_ret], "o", color="#5E3F8C", ms=8)
    ax[0].text(c.D_elec * 1e9 - 1.2, d_ret + 2.0, f"{d_ret:.1f} kT",
               fontsize=9, color="#5E3F8C", ha="right")
    ax[0].plot([d_star * 1e9], [DELTA_SMTJ], "s", color="#A82038", ms=8)
    ax[0].text(d_star * 1e9 + 1.0, DELTA_SMTJ + 2.4,
               f"{d_star*1e9:.0f} nm", fontsize=9, color="#A82038")
    ax[0].text(33, 25, "as-built stack\n" + r"$K_i\pm1\%$ envelope",
               fontsize=9, color="#5E3F8C", ha="right")
    ax[0].text(46, 11.2, r"$K_i$ trimmed $-$%.0f%%" % trim_pct,
               fontsize=9, color="#B8860B")
    ax[0].set_xlabel(r"electrical diameter $D_\mathrm{elec}$ (nm)")
    ax[0].set_ylabel(r"retention $\Delta = E_b/k_BT$ (geometry)")
    ax[0].set_title("Retention barrier from the structural set")
    ax[0].grid(alpha=0.3)

    ax[1].loglog(pitches * 1e9, dp, color="#5E3F8C", lw=2)
    ax[1].axhline(DP_BUDGET, color="grey", ls=":", lw=1.2)
    ax[1].axvspan(24, pitch_star * 1e9, color="#A82038", alpha=0.06)
    ax[1].text(np.sqrt(24 * pitch_star * 1e9), 2.5e-6, "budget region\n(FET-less BEOL)",
               fontsize=8.5, color="#A82038", ha="center")
    ax[1].axvline(30, color="0.35", ls="-.", lw=1.4)
    ax[1].text(30, dp.max() * 0.3, " conventional-memory rule (~30 nm)",
               rotation=90, fontsize=9, color="0.35", va="top")
    ax[1].axvline(PITCH_2T * 1e9, color="#1A6B5A", ls="--", lw=1.6)
    ax[1].text(PITCH_2T * 1e9, dp.max() * 0.3, " 2T cell pitch", rotation=90,
               fontsize=9, color="#1A6B5A", va="top")
    ax[1].plot([PITCH_2T * 1e9], [dp_2t], "o", color="#1A6B5A", ms=7, zorder=5)
    ax[1].annotate(r"$\delta p \approx 10^{%d}$" % np.round(np.log10(dp_2t)),
                   xy=(PITCH_2T * 1e9, dp_2t), xytext=(PITCH_2T * 1e9 * 0.16, dp_2t * 2.2),
                   fontsize=9, color="#1A6B5A",
                   arrowprops=dict(arrowstyle="->", color="#1A6B5A", lw=1.0))
    ax[1].axvline(pitch_star * 1e9, color="#A82038", ls="--", lw=1.6)
    ax[1].text(pitch_star * 1e9, dp.min() * 3, f" 1% shift at "
               f"{pitch_star*1e9:.0f} nm", rotation=90, fontsize=9,
               color="#A82038", va="bottom")
    ax[1].set_xlim(left=24)
    ax[1].set_xlabel("array pitch (nm)")
    ax[1].set_ylabel(r"worst-case neighbour $\delta p$ at $p=1/2$")
    ax[1].set_title("Dipolar crosstalk pitch rule")
    ax[1].grid(alpha=0.3, which="both")
    fig.tight_layout()
    out = REPO / "figures" / "structure_consistency.png"
    fig.savefig(out, dpi=150)
    print(f"figure saved: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
