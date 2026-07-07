"""22 -- Sensitivity audit of the 9-architecture training-energy ranking.

Companion to Experiment 13: sweeps every energy constant of the training
energy model through a provenance-scaled band, one at a time, and reports

  * a tornado chart of the two headline ratios -- CMOS p-bit / sMTJ and
    sMTJ / STT-MRAM -- over each parameter band;
  * exact pairwise rank-reversal multipliers (every architecture total is
    affine in every single constant, so the crossing point is closed-form);
  * the one-at-a-time envelope of both headline ratios.

Bands by provenance tier (see ``tech_params.py`` docstrings):

  * physical      x0.9  - x1.1   e_smtj_write (wafer-calibrated V^2 t/R,
                                  swept through t_write which enters the
                                  energy linearly)
  * sky130        x0.5  - x2     e_smtj_read / e_dac_step / e_count_inc
                                  (extracted or stdcell-estimated, ~2x
                                  stated uncertainty)
  * provisional   x1/3  - x3     e_int8_mac, e_sram_byte, the 5 pJ CMOS
                                  p-bit update, the 3 fJ PRNG draw, and
                                  every MEMORIES read/write constant

Outputs:
  runs/22_energy_sensitivity_<ts>/tornado.csv          per-parameter sweep
  runs/22_energy_sensitivity_<ts>/reversal_boundaries.csv
  figures/22_energy_sensitivity_tornado.png

Run from the repo root:

    python experiments/22_energy_sensitivity.py
"""

from __future__ import annotations

import csv
import dataclasses
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

BASELINE_CSV = REPO / "runs" / "13_training_energy_20260706_225408" / "breakdown.csv"

# Bands by provenance tier (low/high multipliers)
TIER_BANDS = {
    "physical": (0.9, 1.1),
    "sky130": (0.5, 2.0),
    "provisional": (1.0 / 3.0, 3.0),
}


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from smtj_pbnn_sim.ppa import default_28nm, network_training_energy
    from smtj_pbnn_sim.ppa import tech_params as tp_mod
    from smtj_pbnn_sim.utils.io import make_run_dir

    MEMORIES = tp_mod.MEMORIES

    layer_dims = [(1024, 784), (1024, 1024), (10, 1024)]
    batch, n_epochs, train_size, T = 128, 20, 60000, 4
    n_steps = ((train_size + batch - 1) // batch) * n_epochs  # 9380

    ARCHS = [
        ("PBNN sMTJ (T=4)", "pbnn", {}),
        ("PBNN CMOS p-bit (T=4)", "pbnn_stoch", {"storage": "cmos_pbit"}),
        ("PBNN stoch-ReRAM (T=4)", "pbnn_stoch", {"storage": "stoch_reram"}),
        ("PBNN CMOS-PRNG (T=4)", "pbnn_stoch", {"storage": "cmos_prng"}),
        ("FP-NN STT-MRAM", "fp", ("memory", "stt_mram")),
        ("FP-NN ReRAM", "fp", ("memory", "reram")),
        ("FP-NN PCRAM", "fp", ("memory", "pcram")),
        ("FP-NN FeRAM", "fp", ("memory", "feram")),
        ("FP-NN SRAM-CIM", "fp", ("memory", "sram_cim")),
    ]

    def totals(tech) -> dict[str, float]:
        """All-arch totals under the CURRENT (possibly patched) MEMORIES."""
        out = {}
        for label, arch, kw in ARCHS:
            if isinstance(kw, tuple):
                kwargs = {kw[0]: MEMORIES[kw[1]]}
            else:
                kwargs = dict(kw)
            r = network_training_energy(layer_dims, T=T, batch=batch,
                                        n_steps=n_steps, arch=arch,
                                        tech=tech, **kwargs)
            out[label] = r["total"]
        return out

    tech0 = default_28nm()
    base = totals(tech0)

    # ---- self-check against the canonical Experiment-13 run ----------------
    if BASELINE_CSV.exists():
        with open(BASELINE_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ref = float(row["total_J"])
                got = base[row["architecture"]]
                assert abs(got - ref) / ref < 1e-6, (
                    f"baseline drift vs canonical run: {row['architecture']} "
                    f"{got:.6f} != {ref:.6f}")
        print(f"baseline self-check vs {BASELINE_CSV.name}: OK")
    else:
        print("WARNING: canonical run CSV not found; skipping self-check")

    # ---- parameter registry -------------------------------------------------
    # Each entry: (name, tier, evaluate(multiplier) -> totals dict)
    mem0 = {k: MEMORIES[k] for k in MEMORIES}

    def sweep_tech(field):
        def ev(m):
            return totals(dataclasses.replace(tech0, **{field: getattr(tech0, field) * m}))
        return ev

    def sweep_mem(key, field):
        def ev(m):
            MEMORIES[key] = dataclasses.replace(mem0[key], **{field: getattr(mem0[key], field) * m})
            try:
                return totals(tech0)
            finally:
                MEMORIES[key] = mem0[key]
        return ev

    # The 5 pJ p-bit update and 3 fJ PRNG draw are literals inside
    # pbnn_stoch_step_energy; both enter only their own arch's forward term,
    # so scale that component analytically.
    def sweep_pbit(m):
        out = dict(base)
        # forward = n_steps * batch * sum(macs) * T * 5pJ  (all of forward)
        fwd = 44.702997  # from canonical run, forward_J of the p-bit row
        out["PBNN CMOS p-bit (T=4)"] = base["PBNN CMOS p-bit (T=4)"] + fwd * (m - 1.0)
        return out

    def sweep_prng(m):
        out = dict(base)
        macs = sum(r * c for r, c in layer_dims)
        draw = n_steps * batch * macs * T * 3.0e-15
        out["PBNN CMOS-PRNG (T=4)"] = base["PBNN CMOS-PRNG (T=4)"] + draw * (m - 1.0)
        return out

    PARAMS = [
        ("e_smtj_write (V^2t/R, wafer)", "physical", sweep_tech("t_write")),
        ("e_smtj_read (48 fJ SA)", "sky130", sweep_tech("e_smtj_read")),
        ("e_dac_step (34 fJ)", "sky130", sweep_tech("e_dac_step")),
        ("e_count_inc (19 fJ)", "sky130", sweep_tech("e_count_inc")),
        ("e_int8_mac (1 pJ)", "provisional", sweep_tech("e_int8_mac")),
        ("e_sram_byte (5 pJ)", "provisional", sweep_tech("e_sram_byte")),
        ("p-bit update (5 pJ)", "provisional", sweep_pbit),
        ("PRNG draw (3 fJ)", "provisional", sweep_prng),
    ]
    for key in ("stt_mram", "reram", "pcram", "feram", "sram_cim"):
        PARAMS.append((f"{key}.read", "provisional", sweep_mem(key, "e_read_per_bit")))
        PARAMS.append((f"{key}.write", "provisional", sweep_mem(key, "e_write_per_cell")))

    # ---- sweep --------------------------------------------------------------
    SMTJ, PBIT, STT, FERAM = ("PBNN sMTJ (T=4)", "PBNN CMOS p-bit (T=4)",
                              "FP-NN STT-MRAM", "FP-NN FeRAM")
    r_pbit0 = base[PBIT] / base[SMTJ]
    r_stt0 = base[SMTJ] / base[STT]
    print(f"baseline: p-bit/sMTJ = {r_pbit0:.2f}x, sMTJ/STT = {r_stt0:.2f}x, "
          f"sMTJ/FeRAM = {base[SMTJ] / base[FERAM]:.2f}x")

    run_dir = make_run_dir("22_energy_sensitivity", base=REPO / "runs")
    rows_tornado, rows_reversal = [], []
    order0 = sorted(base, key=base.get)

    for name, tier, ev in PARAMS:
        lo_m, hi_m = TIER_BANDS[tier]
        t_lo, t_hi = ev(lo_m), ev(hi_m)
        rows_tornado.append({
            "param": name, "tier": tier, "band_lo": lo_m, "band_hi": hi_m,
            "smtj_lo": t_lo[SMTJ], "smtj_hi": t_hi[SMTJ],
            "ratio_pbit_lo": t_lo[PBIT] / t_lo[SMTJ],
            "ratio_pbit_hi": t_hi[PBIT] / t_hi[SMTJ],
            "ratio_stt_lo": t_lo[SMTJ] / t_lo[STT],
            "ratio_stt_hi": t_hi[SMTJ] / t_hi[STT],
        })
        # pairwise rank reversals: totals are affine in the multiplier, so
        # interpolate each arch between the two endpoint evaluations.
        for i, a in enumerate(order0):
            for b in order0[i + 1:]:
                d_lo = t_lo[b] - t_lo[a]
                d_hi = t_hi[b] - t_hi[a]
                if (d_lo < 0) != (d_hi < 0):  # order flips inside the band
                    # affine in m: d(m) = d(lo) + (d(hi)-d(lo))*(m-lo)/(hi-lo)
                    m_star = lo_m + (0.0 - d_lo) * (hi_m - lo_m) / (d_hi - d_lo)
                    rows_reversal.append({
                        "param": name, "tier": tier,
                        "arch_low": a, "arch_high": b,
                        "reversal_multiplier": round(m_star, 3),
                    })

    env_pbit = ([r["ratio_pbit_lo"] for r in rows_tornado]
                + [r["ratio_pbit_hi"] for r in rows_tornado])
    env_stt = ([r["ratio_stt_lo"] for r in rows_tornado]
               + [r["ratio_stt_hi"] for r in rows_tornado])
    print(f"one-at-a-time envelope: p-bit/sMTJ = {min(env_pbit):.2f}-{max(env_pbit):.2f}x, "
          f"sMTJ/STT = {min(env_stt):.2f}-{max(env_stt):.2f}x")
    print(f"rank reversals inside bands: {len(rows_reversal)}")
    for r in rows_reversal:
        print(f"  {r['param']:24s} x{r['reversal_multiplier']:<6} flips "
              f"{r['arch_low']}  <->  {r['arch_high']}")

    with open(run_dir / "tornado.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_tornado[0]))
        w.writeheader()
        w.writerows(rows_tornado)
    with open(run_dir / "reversal_boundaries.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["param", "tier", "arch_low", "arch_high",
                                          "reversal_multiplier"])
        w.writeheader()
        w.writerows(rows_reversal)
    print(f"CSVs written to {run_dir}")

    # ---- tornado figure ------------------------------------------------------
    plt.rcParams.update({"font.family": "Arial", "font.size": 12})
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6), sharey=True)
    show = sorted(rows_tornado,
                  key=lambda r: abs(r["ratio_pbit_hi"] - r["ratio_pbit_lo"])
                  + abs(r["ratio_stt_hi"] - r["ratio_stt_lo"]),
                  reverse=True)[:10]
    show = show[::-1]
    labels = [r["param"] for r in show]
    tier_color = {"physical": "#1a7a4a", "sky130": "#2e5fa3", "provisional": "#b3541e"}
    for ax, (klo, khi, base_v, title) in zip(axes, [
            ("ratio_pbit_lo", "ratio_pbit_hi", r_pbit0,
             "CMOS p-bit / sMTJ total-energy ratio"),
            ("ratio_stt_lo", "ratio_stt_hi", r_stt0,
             "sMTJ / STT-MRAM total-energy ratio")]):
        for y, r in enumerate(show):
            lo, hi = sorted((r[klo], r[khi]))
            ax.barh(y, hi - lo, left=lo, height=0.62,
                    color=tier_color[r["tier"]], alpha=0.85)
        ax.axvline(base_v, color="k", lw=1.2, ls="--")
        ax.text(base_v, len(show) - 1.2, f" baseline {base_v:.2f}x",
                fontsize=11, ha="left", va="top")
        if title.startswith("sMTJ"):
            ax.axvline(1.0, color="#888888", lw=1.0, ls=":")
            ax.text(1.0, -0.45, " parity", fontsize=10, color="#555555",
                    ha="left", va="bottom")
        ax.set_title(title, fontsize=13)
        ax.set_xlabel("ratio under one-at-a-time parameter band")
        ax.grid(axis="x", alpha=0.3)
    axes[0].set_yticks(range(len(show)))
    axes[0].set_yticklabels(labels, fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.85)
               for c in tier_color.values()]
    axes[1].legend(handles,
                   ["physical (x0.9-1.1)", "sky130 (x0.5-2)", "provisional (x1/3-3)"],
                   loc="lower right", fontsize=10, framealpha=0.9)
    fig.tight_layout()
    out_png = REPO / "figures" / "22_energy_sensitivity_tornado.png"
    fig.savefig(out_png, dpi=150)
    print(f"figure saved: {out_png.relative_to(REPO)}")


if __name__ == "__main__":
    main()
