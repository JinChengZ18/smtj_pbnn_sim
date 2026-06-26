#!/bin/bash
# Track B (errata R3/R5): Magic resistance extraction of the sky130 sheet-R calibration straps.
# Runs from an ASCII ext4 build dir (the /tmp-tmpfs idle-wipe reason; same pattern as run_drc.sh).
#
# INVOKE from this dir:
#   wsl -d Ubuntu-24.04-EDA -- bash -lc \
#     'cd "<repo>/eda/extraction/writeline" && bash run_extresist.sh'
set -u
BUILD=/home/lenovo/smtj_eda_build
RC=/opt/pdk/sky130A/libs.tech/magic/sky130A.magicrc
TOP=writeline_straps

mkdir -p "$BUILD"
cp writeline_straps.gds "$BUILD/wl.gds"
cp "$RC" "$BUILD/.magicrc"
sync
sz=$(wc -c < "$BUILD/wl.gds" 2>/dev/null || echo 0)
echo "staged $sz bytes -> $BUILD/wl.gds"
[ "$sz" -gt 200 ] || { echo "ERROR: GDS copy did not land; re-run."; exit 1; }

export PDK_ROOT=/opt/pdk PDK=sky130A
cd "$BUILD"
cat > extres.tcl <<EOF
gds read wl.gds
load $TOP
select top cell
extract do resistance
extract all
extresist tolerance 1
extresist all
ext2spice extresist on
ext2spice cthresh infinite
ext2spice -o wl_res.spice
puts "EXTRES_DONE"
quit -noprompt
EOF

magic -dnull -noconsole -rcfile .magicrc extres.tcl > extres.log 2>&1
echo "--- extres.log tail ---"; tail -15 extres.log
echo "--- wl_res.spice (resistor lines) ---"
grep -iE "^R|\.subckt|^\*" wl_res.spice 2>/dev/null | head -80 || echo "(no spice produced)"
echo "  netlist: $BUILD/wl_res.spice"
echo "  log:     $BUILD/extres.log"
