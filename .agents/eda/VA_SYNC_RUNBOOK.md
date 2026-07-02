# VA-model sync runbook (canonical vgsot-sim -> smtj_pbnn_sim)

**Status: WAITING.** The canonical vgsot-sim (`D:\Documents\Graduation Project-2026\02MRAMSim\vgsot-sim`, branch `recal-and-article-sync`) is mid-flight with another stream's modifications (RTN-reservoir research landing: commits `a947912..21acff3` = fig2.1 fix / chapter02.docx regen / fig2.19 / fig2.20+tab2.14; working tree: Chapter02 fig-set regeneration, `plot_ser_mc.py` / `plot_single_trajectory.py` edits, `.gitignore`, new `article/ppt/`). Per user directive (2026-07-02): **do not sync until that side's verification passes.**

**Trigger:** user says the canonical verification passed.

## Parked work (apply FIRST when unblocked)

- [`pending_vgsot_destale.patch`](pending_vgsot_destale.patch) — the 7-file `theta_SH` 0.04->0.066 doc de-stale (README.md, docs/{technical_details,parameters,cases,api}.md, va/README.md, src/vgsot_sim/configs.py:231 comment). 27 insertions / 25 deletions; verified PURE against canonical HEAD `21acff3` (the 4 intervening commits touched none of these files). The same edits also sit **uncommitted in the canonical working tree** — if the other stream commits them along the way, discard the patch; if it reverts them, `git apply --3way` the patch.
- Still-stale rows NOT yet fixed (were entangled with the other stream's files, deferred): `CLAIMS.md` rows tagging the completed #12 recal as pending ("LLG <-> behavioural cross-validation ... will not reproduce until θ_SH recalibration (#12)"; "`θ_SH=0.04` gives V_th(0.75 ns)≈894 mV ... needs recal (#12)"; clarification "~43% ... will be removed when #12 recalibrates" — true figure is ~40%), and `docs/IMPLEMENTATION_STATUS.md` bias-field row "defaults to 200 Oe along +x, configs.py:69-72" (actual: -50 Oe along -y, configs.py:125-127). Re-locate line numbers after their commits land.

## Sync steps

1. **Canonical health:** clean tree, `PYTHONPATH=src python -m pytest tests/ -q` green, record HEAD hash.
2. **Diff the engine surface since `877e4ec`:** `dynamic_switching*.py`, `anisotropy.py`, `configs.py`, `time_series_cases.py`, `initialize.py`, `material_temperature.py`, plus the integrator work (`scripts/02_integrator/`, `tests/test_integrator_order.py`, `scripts/11_*`). Map each change to its `va/llg/vgsot_llg.va` impact. If nothing touches the RHS/parameters, the VA sync is a submodule pointer bump only.
3. **If the engine changed:** mirror the change into `va/llg/vgsot_llg.va`; `openvaf` compile; ngspice `tb_switch.spice`; `va/llg/cross_validate.py` vs the Python engine (gate tol 0.02; last-good `max|dmz|=0.00793`, equilibrium `4.1e-6`, n=3011, |m| drift 2.8e-4). If the calibration moved: re-run `scripts/09_simulation_figures/calibrate_to_experiment.py`, update the configs comment + docs + chapter02 figs 08/09/10.
4. **Close out docs:** apply the parked de-stale patch + fix the CLAIMS/IMPLEMENTATION_STATUS residual rows; commit canonical (push only on explicit user OK).
5. **smtj_pbnn_sim side:** `git fetch` inside `eda/vendor/vgsot-sim`, checkout the verified hash (pointer bump); re-run `eda/testbenches/llg_validate.py` (200 trials; last-good threshold 0.886 V vs behavioral 0.896 V = 0.40*V_T, RMSE 0.157, eta_c slope note) + `run_regression.py`; if metrics shift, update `article/chapter04.md:219/223` + fig 4.21 (`eda/gen_supplement_figs.py` fig1) + regenerate `chapter04.docx` (pp `$$`->`$` + pandoc).
6. **Commit smtj_pbnn_sim** (local; push/PR only on user OK). Update `.agents/MEMORY.md` + the Claude project memory.
