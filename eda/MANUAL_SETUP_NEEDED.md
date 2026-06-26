# Manual setup needed (time-boxed, do when convenient)

Items that need a hands-on step before the corresponding EDA work can proceed. Everything
**not** listed here is already automated/working (P1 regression, P2–P7 first-cuts, Hero A1
SA + offset MC + closed-loop + B5 readout mapping + GDS export + **DRC 0-violations**).

Last updated: 2026-06-26 (Magic upgrade done; repo on English path).

---

## 1. Update Magic to >= 8.3.306  (routing -> LVS -> PEX)  — ✅ completed 2026-06-26

**Done.** Magic was rebuilt from source to **8.3.668** (>> the required 8.3.306) into
`/usr/local/bin`. Verified two ways:

```bash
magic --version        # -> 8.3.668   (/usr/local/bin/magic wins; the stale apt 8.3.105 is gone)
echo 'puts OK; quit -noprompt' | \
  magic -dnull -noconsole -T /opt/pdk/sky130A/libs.tech/magic/sky130A.tech
#   -> prints OK, exit 0, NO "requires magic-8.3.306" error
#   -> 'Using technology "sky130A", version 1.0.349'  (techfile loads cleanly)
```

This **unblocks the Magic/TCL `routing -> LVS -> PEX` route** that was version-blocked when the
Hero(A1) GDS was first produced with KLayout PCells (the GDS itself stays valid — KLayout and Magic
read the same `sa_devices.gds`).

**First PEX step already validated (2026-06-26):** `eda/hero/layout/run_pex.sh` runs
`gds read -> load -> extract all -> ext2spice` on `sa_devices.gds` and produces
`sa_pex.spice` with all **9 transistors** (5 `nfet_01v8` + 4 `pfet_01v8`, correct W/L) plus
device/local-interconnect parasitic caps. The Magic extract→ext2spice toolchain therefore works
end-to-end on this machine — not just the techfile load.

**Remaining on this branch (the real R3/R5 numbers):** the current GDS is **device-level** (no
inter-device routing, no port labels), so the PEX above is a toolchain validation, not yet a
meaningful IR/energy result. To get there:
1. add inter-device **routing** to the SA layout (KLayout-Python or GUI; the labor-intensive part);
2. **Netgen LVS** layout vs `eda/hero/strongarm_sa.spice` — **caveat:** `/usr/bin/netgen` (apt) is
   the *mesh-generator* netgen (Schoeberl/Vienna), **NOT** the LVS netgen (Tim Edwards / open_pdks);
   verify/install the correct `netgen` before the LVS step;
3. re-run `run_pex.sh` (add `extresist` for R) → post-layout offset/energy → feeds errata **R3**
   (IR-drop) and **R5** (end-to-end energy).

Build recipe used (kept for reference / other machines): install `tcl-dev tk-dev libcairo2-dev`
(plus `build-essential m4 tcsh flex bison libx11-dev libncurses-dev` + mesa GLU) **before**
`./configure` (otherwise it silently builds a non-Tcl Magic that can't load sky130A), then
`make -j$(nproc) && sudo make install`, `sudo apt remove -y magic`, `hash -r`.

---

## 2. Project path: pure-English?  — completed on 2026-06-26

The repository has been moved from the old non-ASCII Windows parent path
(`D:\Documents\毕业设计-2026年5月10日\04PBNN仿真`) to the English path:
`D:\Documents\Graduation Project-2026\04PBNNSim\smtj_pbnn_sim`.

This avoids the KLayout `-rd input=<path>` UTF-8 parsing issue at the Windows path level. The EDA
flow still stages into the ASCII ext4 build dir `~/smtj_eda_build` on the distro
(`eda/hero/layout/run_drc.sh` — DRC passes 0 violations through it), and Python scripts continue to
use `Path(__file__).resolve()` so they remain path-independent.

Post-move maintenance already performed:
- rewired `.git/worktrees/*/gitdir` and each `.claude/worktrees/*/.git` linked-worktree pointer;
- updated Claude/Codex permission entries in `.claude/settings.local.json` and worktree-local
  `.claude/settings.local.json` files;
- added `.agents/MEMORY.md` with the path migration note for future maintenance agents.

Remaining historical references to the old path should be treated as context only, not as an
operational root.

---

## 3. Install the LVS netgen (Tim Edwards / open_pdks)  — needed for the LVS step  — ~10 min

**Why:** with Magic upgraded (§1), the next step on the SA layout is **LVS** (layout vs
`eda/hero/strongarm_sa.spice`). But the only `netgen` on `Ubuntu-24.04-EDA` is `/usr/bin/netgen` —
the **mesh generator** (Joachim Schoeberl / Vienna, `NETGEN-6.2.x`), a completely different program
that happens to share the binary name. The **LVS netgen** (R. Timothy Edwards, shipped with
open_pdks; prints `netgen LVS …` / sources `sky130A_setup.tcl`) is **not installed** (confirmed:
`find / -name netgen -type f` returns only the apt mesh one). LVS cannot run until the right netgen
is present.

**Fix** (build from source into `/usr/local`, so it doesn't clash with the apt mesh netgen):
```bash
cd ~ && rm -rf netgen-lvs && git clone https://github.com/RTimothyEdwards/netgen.git netgen-lvs
cd ~/netgen-lvs && ./configure && make -j$(nproc) && sudo make install   # -> /usr/local/bin/netgen
hash -r
/usr/local/bin/netgen -batch lvs    # should print netgen LVS usage, NOT mesh-generator banner
```
(Or just use the IIC-OSIC-TOOLS Docker image, which bundles the correct netgen + magic + sky130A —
the Phase-0 gate in `STATUS.md`.) After install, run LVS with the sky130A setup:
`netgen -batch lvs "<extracted>.spice <topcell>" "strongarm_sa.spice <topcell>" /opt/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl`.

---

## Not blocking (FYI)
- `tools.local.json` holds machine-local `E:\EDA\...` Windows paths (ngspice/openvaf); gitignored,
  regenerate per machine. Discovered by scripts via env/config/PATH.
- KLayout sky130 PCells need `pandas` in the system python3.12
  (`pip3 install --break-system-packages pandas`) — already installed on this machine.
