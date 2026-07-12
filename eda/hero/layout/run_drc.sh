#!/bin/bash
# Reproducible sky130 DRC of the SA device GDS, run from an ASCII build dir.
#
# WHY a build dir: /tmp (tmpfs) is wiped when the WSL distro idle-stops -- so DRC
# would see 0 polygons. Fix: stage the GDS into a PERSISTENT ASCII ext4 dir
# (~lenovo on the distro disk) and run DRC there.
# (Historical: the repo used to live under a non-ASCII path (毕业设计/仿真) which also
#  mangled KLayout's `-rd input=<path>` UTF-8 arg -- that reason is GONE since the
#  2026-06-26 move to a pure-English path; the /tmp-tmpfs reason above remains.)
#
# INVOKE from the layout dir (the GDS is referenced by a relative ASCII name, and bash
# reads THIS file directly so its variables are not subject to Git-Bash->wsl mangling):
#
#   wsl -d Ubuntu-24.04-EDA -- bash -lc \
#     'cd "<repo>/eda/hero/layout" && bash run_drc.sh'
#
# RESULT (2026-06-26): "0 DRC violations" -- CORRECTED 2026-07-08: that run passed
# NO feature flags, and this deck runs no rules without $feol/$beol/$offgrid (always
# reports 0 = false negative; caught by a positive control while building the 2T
# cell, see README "DRC 特性开关"). With flags the device-level SA GDS shows ~542
# items: mostly *_OFFGRID (PCell emits 0.001um off-grid coords in guard rings /
# some widths) plus m1.5 x24 / li.3 x6 -- PCell edge artifacts, not design errors;
# fix = the 5-dbu grid snap used by gen_2t_cell.py, scheduled with the 1.7 routing
# window. Flags are now passed below.
set -u
BUILD=/home/lenovo/smtj_eda_build
DECK=/opt/pdk/sky130A/libs.tech/klayout/drc/sky130A_mr.drc
TOP=strongarm_sa_devs

mkdir -p "$BUILD"
cp sa_devices.gds "$BUILD/sa.gds"
sync
sz=$(wc -c < "$BUILD/sa.gds" 2>/dev/null || echo 0)
echo "staged $sz bytes -> $BUILD/sa.gds"
[ "$sz" -gt 1000 ] || { echo "ERROR: GDS copy did not land (cold-distro fs race); re-run."; exit 1; }

export PDK_ROOT=/opt/pdk PDK=sky130A
klayout -b -r "$DECK" \
  -rd input="$BUILD/sa.gds" -rd report="$BUILD/sa_drc.xml" -rd top_cell="$TOP" \
  -rd feol=1 -rd beol=1 -rd offgrid=1 \
  > "$BUILD/drc.log" 2>&1
v=$(grep -c "<item>" "$BUILD/sa_drc.xml" 2>/dev/null || true)   # grep -c exits 1 on 0 matches
echo "DRC done: ${v:-0} violations"
echo "  report: $BUILD/sa_drc.xml"
echo "  log:    $BUILD/drc.log"
grep -E "Total elapsed" "$BUILD/drc.log" | tail -1
