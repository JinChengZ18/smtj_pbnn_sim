#!/bin/bash
# Reproducible sky130 DRC of the SA device GDS, run from an ASCII build dir.
#
# WHY a build dir: the project lives under a non-ASCII path (毕业设计/仿真).
# KLayout's `-rd input=<path>` mangles UTF-8 arguments (truncates the path), and
# /tmp (tmpfs) is wiped when the WSL distro idle-stops -- so DRC saw 0 polygons.
# Fix: stage the GDS into a PERSISTENT ASCII ext4 dir (~lenovo on the distro disk)
# and run DRC there, keeping the non-ASCII path out of every tool argument.
#
# INVOKE from the layout dir (the literal `cd` tolerates the CJK path; the GDS is
# then referenced by a relative ASCII name, and bash reads THIS file directly so its
# variables are not subject to the Git-Bash->wsl arg mangling):
#
#   wsl -d Ubuntu-24.04-EDA -- bash -lc \
#     'cd "<repo>/eda/hero/layout" && bash run_drc.sh'
#
# RESULT (2026-06-26): 0 DRC violations on strongarm_sa_devs (device-level; routing
# DRC follows once interconnect is drawn). drc.log/sa_drc.xml land in $BUILD.
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
  > "$BUILD/drc.log" 2>&1
v=$(grep -c "<item>" "$BUILD/sa_drc.xml" 2>/dev/null || true)   # grep -c exits 1 on 0 matches
echo "DRC done: ${v:-0} violations"
echo "  report: $BUILD/sa_drc.xml"
echo "  log:    $BUILD/drc.log"
grep -E "Total elapsed" "$BUILD/drc.log" | tail -1
