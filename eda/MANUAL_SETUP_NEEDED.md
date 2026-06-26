# Manual setup needed (time-boxed, do when convenient)

Items that need a hands-on step before the corresponding EDA work can proceed. Everything
**not** listed here is already automated/working (P1 regression, P2–P7 first-cuts, Hero A1
SA + offset MC + closed-loop + B5 readout mapping + GDS export + **DRC 0-violations**).

Last updated: 2026-06-26.

---

## 1. Update Magic to >= 8.3.306  (unblocks layout routing -> LVS -> PEX)  — ~10-20 min

**Why:** the installed Magic is **8.3.105** (Ubuntu-24.04 apt cap; `apt upgrade` can never reach
8.3.306). The sky130A techfile hard-requires it — `/opt/pdk/sky130A/libs.tech/magic/sky130A.tech`
line 19 literally says `requires magic-8.3.306`, so the techfile refuses to load and the scripted
Magic/TCL layout + `ext2spice` PEX route is blocked. The current GDS was therefore produced with
**KLayout PCells** instead (works, DRC-clean); Magic is only needed for the *routing -> LVS -> PEX*
branch below.

**Fix:** build the latest Magic from source (currently 8.3.667 >> 8.3.306) into `/usr/local`.

> **CRITICAL pitfall first:** `tcl-dev`, `tk-dev`, `libcairo2-dev` are **not yet installed** on
> this distro (only `libx11-dev` is); there is no `tclConfig.sh`. If you skip them, `./configure`
> *silently* builds a **non-Tcl** Magic that cannot load sky130A. Install the deps BEFORE
> `./configure`, and read the configure output to confirm it reports "Tcl/Tk … found".

Run inside the distro (`wsl.exe -d Ubuntu-24.04-EDA -- bash -lc '<cmd>'` from Windows — note the
distro name is **`Ubuntu-24.04-EDA`**, not plain `Ubuntu-24.04`):

```bash
sudo apt update
sudo apt install -y git build-essential m4 tcsh csh flex bison \
     libx11-dev tcl-dev tk-dev libcairo2-dev libncurses-dev \
     libglu1-mesa-dev freeglut3-dev mesa-common-dev
ls /usr/lib/x86_64-linux-gnu/tclConfig.sh /usr/lib/x86_64-linux-gnu/tkConfig.sh   # must exist now
cd ~ && rm -rf magic && git clone https://github.com/RTimothyEdwards/magic.git
cd ~/magic
./configure            # confirm it prints that Tcl AND Tk were found
make -j$(nproc)
sudo make install      # installs to /usr/local/bin
sudo apt remove -y magic || true   # drop the stale 8.3.105 at /usr/bin
hash -r
which -a magic         # /usr/local/bin/magic should win
```

**Verify (the real test is the techfile load, not just `--version`):**
```bash
magic --version        # -> 8.3.667 (NOT 8.3.105; if still 8.3.105, run `hash -r`, fix PATH)
echo 'puts "OK"; quit -noprompt' | \
  magic -dnull -noconsole -T /opt/pdk/sky130A/libs.tech/magic/sky130A.tech
# success = prints OK, exit 0, NO "requires magic-8.3.306" error
```

Lower-risk alternative if you don't want to touch system dirs:
`./configure --prefix=$HOME/eda/magic` then prepend `$HOME/eda/magic/bin` to PATH (leaves the
apt magic untouched, avoids the PATH-shadowing pitfall).

**What this unblocks (the "导出版图" follow-on, currently the only Magic-gated work):**
SA inter-device **routing** -> **Netgen LVS** (layout vs `eda/hero/strongarm_sa.spice`) ->
**`ext2spice` PEX** -> post-layout offset/energy corner sim. Feeds errata R3 (IR-drop) and R5
(end-to-end energy). KLayout can also do routing+LVS if you prefer to stay off Magic.

---

## 2. Project path: pure-English?  — already handled non-destructively; full move NOT recommended

The non-ASCII project path (`毕业设计-2026年5月10日/04PBNN仿真`) is what broke KLayout's
`-rd input=<path>` UTF-8 parsing. **This is already solved** without moving anything: EDA tools now
stage into an **ASCII ext4 build dir** `~/smtj_eda_build` on the distro and run there
(`eda/hero/layout/run_drc.sh` — DRC passes 0 violations through it). Python scripts use
`Path(__file__).resolve()` and are path-independent.

**Recommendation (from a repo survey): keep the repo where it is.** Moving the whole tree to an
ASCII path is high-cost / low-gain — it would require rewiring **5 git worktrees**
(`.git/worktrees/*/gitdir` hold absolute paths), orphan the auto-memory `MEMORY.md` (its folder
name encodes the CJK path → loses session continuity), and risk a half-migrated state. The only
hardcoded absolute path in the repo is the intentional `~/smtj_eda_build` in `run_drc.sh`.

If you DO want a full move later (e.g. team handoff), it's a separate controlled step:
`git worktree move` each worktree (or prune + recreate), regenerate the memory index, re-run the
full test suite (`gen_golden` / `run_regression` / `hero_mnist_sweep`), then commit. Deferred — not
needed for the current roadmap (Hero A1 + second paper C3).

---

## Not blocking (FYI)
- `tools.local.json` holds machine-local `E:\EDA\...` Windows paths (ngspice/openvaf); gitignored,
  regenerate per machine. Discovered by scripts via env/config/PATH.
- KLayout sky130 PCells need `pandas` in the system python3.12
  (`pip3 install --break-system-packages pandas`) — already installed on this machine.
