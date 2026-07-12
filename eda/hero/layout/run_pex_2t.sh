#!/bin/bash
# Reproducible sky130 PEX of the 2T SOT-sMTJ cell GDS via Magic (MTJ plan L1),
# same build-dir pattern as run_pex.sh. The black-box layers 200/0, 201/0 are
# unknown to the Magic techfile and are ignored -- extraction covers exactly
# the CMOS part (2 FETs + local interconnect parasitics).
#
# INVOKE from the layout dir:
#   wsl -d Ubuntu-24.04-EDA -- bash -lc \
#     'cd "<repo>/eda/hero/layout" && bash run_pex_2t.sh'
set -u
BUILD=/home/lenovo/smtj_eda_build
RC=/opt/pdk/sky130A/libs.tech/magic/sky130A.magicrc
TOP=cell2t_smtj

mkdir -p "$BUILD"
cp cell2t.gds "$BUILD/cell2t.gds"
cp "$RC" "$BUILD/.magicrc"
sync
sz=$(wc -c < "$BUILD/cell2t.gds" 2>/dev/null || echo 0)
echo "staged $sz bytes -> $BUILD/cell2t.gds"
[ "$sz" -gt 1000 ] || { echo "ERROR: GDS copy did not land (cold-distro fs race); re-run."; exit 1; }

export PDK_ROOT=/opt/pdk PDK=sky130A
cd "$BUILD"
cat > pex2t.tcl <<EOF
gds read cell2t.gds
load $TOP
extract all
ext2spice lvs
ext2spice cthresh 0
ext2spice -o cell2t_pex.spice
puts "PEX_DONE devices+C extracted"
quit -noprompt
EOF

rm -f cell2t_pex.spice                       # never show a stale netlist
magic -dnull -noconsole -rcfile .magicrc pex2t.tcl > pex2t.log 2>&1
rc=$?
if [ $rc -ne 0 ] || [ ! -s cell2t_pex.spice ]; then
  echo "ERROR: PEX did not produce a netlist (magic rc=$rc)"
  tail -8 pex2t.log; exit 1
fi
echo "--- pex2t.log tail ---"; tail -8 pex2t.log
echo "--- extracted netlist ---"; cat cell2t_pex.spice
echo "  netlist: $BUILD/cell2t_pex.spice"
echo "NOTE: the BE2/SL met2 island is floating BY DESIGN (black-box-only"
echo "      connection); any testbench using this netlist must attach the"
echo "      SOT/MTJ black-box elements or shunt that node before DC analysis."
