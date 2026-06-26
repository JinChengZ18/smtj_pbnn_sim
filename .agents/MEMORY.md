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