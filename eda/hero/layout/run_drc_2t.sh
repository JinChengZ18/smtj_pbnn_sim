#!/bin/bash
# Reproducible sky130 DRC of the 2T SOT-sMTJ cell GDS (MTJ plan L1), same
# build-dir pattern as run_drc.sh (stage into persistent ASCII ext4 dir; /tmp is
# tmpfs and wiped on WSL idle-stop).
#
# INVOKE from the layout dir:
#   wsl -d Ubuntu-24.04-EDA -- bash -lc \
#     'cd "<repo>/eda/hero/layout" && bash run_drc_2t.sh'
#
# NOTE: the black-box layers 200/0 (MTJ pillar) and 201/0 (SOT track) are not
# part of sky130A; the deck simply never references them, so this DRC covers
# exactly the CMOS/metal part (the L1 DoD scope).
set -u
BUILD=/home/lenovo/smtj_eda_build
DECK=/opt/pdk/sky130A/libs.tech/klayout/drc/sky130A_mr.drc
TOP=cell2t_smtj

mkdir -p "$BUILD"
cp cell2t.gds "$BUILD/cell2t.gds"
sync
sz=$(wc -c < "$BUILD/cell2t.gds" 2>/dev/null || echo 0)
echo "staged $sz bytes -> $BUILD/cell2t.gds"
[ "$sz" -gt 1000 ] || { echo "ERROR: GDS copy did not land (cold-distro fs race); re-run."; exit 1; }

# IMPORTANT (found 2026-07-08 via a positive control): this deck runs NO rules
# unless the feature flags are passed -- without them it always reports 0
# violations (false negative). Cell-level set: feol+beol+offgrid. seal is a
# seal-ring rule (n/a); floating_met flags the black-box-connected met islands
# by design (run it separately as informative if needed).
export PDK_ROOT=/opt/pdk PDK=sky130A
klayout -b -r "$DECK" \
  -rd input="$BUILD/cell2t.gds" -rd report="$BUILD/cell2t_drc.xml" -rd top_cell="$TOP" \
  -rd feol=1 -rd beol=1 -rd offgrid=1 \
  > "$BUILD/drc2t.log" 2>&1
v=$(grep -c "<item>" "$BUILD/cell2t_drc.xml" 2>/dev/null || true)
echo "DRC done: ${v:-0} violations"
echo "  report: $BUILD/cell2t_drc.xml"
echo "  log:    $BUILD/drc2t.log"
if [ "${v:-0}" != "0" ]; then
  echo "--- violation categories ---"
  grep -oE "<category>[^<]+</category>" "$BUILD/cell2t_drc.xml" | sort | uniq -c | sort -rn | head -20
fi
