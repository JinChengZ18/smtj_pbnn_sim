# Agent Memory

> Append-only log of facts maintenance agents (Claude / Codex / others) need across sessions.
> Orientation + conventions live in [`README.md`](README.md); this file is the dated change log.

- 2026-06-26: Repository path migrated.
  - Old root: `D:\Documents\毕业设计-2026年5月10日\04PBNN仿真\smtj_pbnn_sim`
  - New root: `D:\Documents\Graduation Project-2026\04PBNNSim\smtj_pbnn_sim`
  - Maintenance agents should use the new English path only. The old Chinese path should be treated as stale and may no longer exist.
  - Claude/Codex maintenance metadata and linked-worktree pointers were migrated to the new root on 2026-06-26.
  - **Worktrees verified rewired**: `git worktree list` shows all 5 `.claude/worktrees/*` on the new path, **none `prunable`** — the post-move worktree follow-up is DONE (no `git worktree prune` needed).
  - **Stale CJK-path comments refreshed** to "historical" in `eda/hero/layout/run_drc.sh`, `eda/hero/layout/README.md`, `eda/hero/layout/gen_sa_layout.py`, and `eda/STATUS.md`. The ASCII ext4 build dir `/home/lenovo/smtj_eda_build` is STILL required, but now only for the `/tmp`-tmpfs idle-wipe reason (the `-rd input` UTF-8 mangling reason is gone).

- 2026-06-26: **Magic upgraded — PEX route unblocked.**
  - `/usr/local/bin/magic` rebuilt from source to **8.3.668** (>> required 8.3.306); stale apt 8.3.105 removed. sky130A techfile loads cleanly (`Using technology "sky130A", version 1.0.349`).
  - This unblocks the Magic/TCL **routing → LVS → PEX** route (was the only Magic-gated work). `eda/hero/layout/run_pex.sh` validates the `extract → ext2spice` toolchain (9 devices + parasitic C from the device-level GDS). `eda/MANUAL_SETUP_NEEDED.md §1` and `eda/STATUS.md` D8 updated to "done".
  - **LVS gotcha (confirmed):** the LVS netgen (Tim Edwards / open_pdks) is **NOT installed** — the only `netgen` on the distro is `/usr/bin/netgen`, the mesh generator (Schoeberl/Vienna). Build the right one before LVS; recipe in `eda/MANUAL_SETUP_NEEDED.md §3`.
  - WSL distro for all sky130 tooling = **`Ubuntu-24.04-EDA`** (ngspice-46 + OpenVAF-Reloaded + sky130A + KLayout + Magic 8.3.668).

- 2026-06-26: **Phase 0 toolchain gate met natively + Track A/B PEX results.**
  - LVS netgen (Tim Edwards) **1.5.321** built at `~/eda/netgen/bin/netgen` (apt `/usr/bin/netgen` is the mesh generator — don't use it for LVS). So the whole open EDA chain (ngspice/OpenVAF/sky130A/KLayout/Magic 8.3.668/netgen) now runs **natively** — IIC-OSIC-TOOLS Docker is optional, not the Phase-0 blocker the replan assumed.
  - **Track B (R3/R5)** `eda/extraction/writeline/`: Magic `extresist` validated (poly 47.96 vs 48.2 Ω/sq); column write-line round-trip metal R vs 776 Ω — N≤64 negligible, **N=256 met1/met2 = 16.5%** (IR 148 mV → pushes far cell below the 0.8958 V write point → p_sw shift), li1 catastrophic. Route write on met2+/widen/segment.
  - **Track A (R1/R2/R5)** SA layout device set fixed **9→11** (added Mp3/Mp4), DRC 0 violations, 11 MOSFETs + 35.25 fF extract; post-layout SA energy ~23–74 fJ/decision (5–15× the 5 fF read placeholder → R1); netgen LVS toolchain validated (device-level). **SA routing + full LVS = GUI last-mile** (`eda/hero/layout/LVS_GUI_CHECKLIST.md`).
  - **Step-executable plan** = `eda/PLAN_execution.md` (innovation main line A0/A1+A2/A3 broken into steps 1.1…3.5 with DoD + this session's status + "5 immediately-actionable" list).