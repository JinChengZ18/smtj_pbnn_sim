#!/bin/bash
# Reproducible sky130 PEX (parasitic extraction) of the SA GDS via Magic, run from
# an ASCII build dir. Unblocked 2026-06-26 by the Magic >=8.3.306 upgrade (now 8.3.668);
# this is the Magic/TCL routing->LVS->PEX route that was version-blocked when the GDS
# was first produced with KLayout PCells (see README.md "Why KLayout").
#
# WHY a build dir (same pattern as run_drc.sh): /tmp is tmpfs and is wiped when the WSL
# distro idle-stops, so stage into a PERSISTENT ASCII ext4 dir and run there. (The old
# non-ASCII-path arg-mangling reason is GONE since the 2026-06-26 repo move to an English
# path, but the /tmp-tmpfs reason remains -- keep the build dir.)
#
# INVOKE from the layout dir:
#   wsl -d Ubuntu-24.04-EDA -- bash -lc \
#     'cd "<repo>/eda/hero/layout" && bash run_pex.sh'
#
# SCOPE: the current sa_devices.gds is DEVICE-LEVEL (no inter-device routing, no port
# labels), so this validates the Magic extract->ext2spice toolchain and yields a
# device+local-interconnect parasitic netlist. Meaningful R3 (IR-drop) / R5 (end-to-end
# energy) numbers need the ROUTED layout (add interconnect -> Netgen LVS -> re-run PEX).
set -u
BUILD=/home/lenovo/smtj_eda_build
TECH=/opt/pdk/sky130A/libs.tech/magic/sky130A.tech
RC=/opt/pdk/sky130A/libs.tech/magic/sky130A.magicrc
TOP=strongarm_sa_devs

mkdir -p "$BUILD"
cp sa_devices.gds "$BUILD/sa.gds"
cp "$RC" "$BUILD/.magicrc"
sync
sz=$(wc -c < "$BUILD/sa.gds" 2>/dev/null || echo 0)
echo "staged $sz bytes -> $BUILD/sa.gds"
[ "$sz" -gt 1000 ] || { echo "ERROR: GDS copy did not land (cold-distro fs race); re-run."; exit 1; }

export PDK_ROOT=/opt/pdk PDK=sky130A
cd "$BUILD"
cat > pex.tcl <<EOF
gds read sa.gds
load $TOP
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice -o sa_pex.spice
puts "PEX_DONE devices+C extracted"
quit -noprompt
EOF

magic -dnull -noconsole -rcfile .magicrc pex.tcl > pex.log 2>&1
echo "--- pex.log tail ---"; tail -15 pex.log
echo "--- extracted devices (MOSFET count) ---"
grep -cE "^X|sky130_fd_pr__" sa_pex.spice 2>/dev/null || echo 0
echo "--- sa_pex.spice head ---"; head -30 sa_pex.spice 2>/dev/null || echo "(no spice produced)"
echo "  netlist: $BUILD/sa_pex.spice"
echo "  log:     $BUILD/pex.log"
