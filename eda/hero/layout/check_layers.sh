#!/bin/bash
# One-shot helper: confirm candidate black-box GDS layers are unused by sky130A
# (KLayout .lyp and Magic .tech). Used while building gen_2t_cell.py (L1).
#
# INVOKE (WSL):
#   wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd "<repo>/eda/hero/layout" && bash check_layers.sh'
set -u
LYP=/opt/pdk/sky130A/libs.tech/klayout/tech/sky130A.lyp
TECH=/opt/pdk/sky130A/libs.tech/magic/sky130A.tech

echo "== lyp direct hits for 200/ 201/ 202/ =="
grep -E '<source>(200|201|202)/' "$LYP" || echo "(none)"

echo "== lyp layer/datatype pairs with layer >= 128 =="
grep -oE '<source>[0-9]+/[0-9]+@1' "$LYP" | grep -oE '[0-9]+/[0-9]+' \
  | awk -F/ '$1 >= 128 {print $1"/"$2}' | sort -t/ -k1,1n -u | tr '\n' ' '; echo

echo "== magic tech calma layer/datatype pairs with layer >= 128 =="
# Magic maps GDS via 'calma <name> <layer> <datatype>' lines (NOT 'gds ...' --
# an earlier grep for 'gds' matched nothing and was a null check; fixed 2026-07-08)
grep -E '^[[:space:]]*calma[[:space:]]' "$TECH" \
  | awk '{print $(NF-1)"/"$NF}' | grep -E '^[0-9]+/[0-9]+$' \
  | awk -F/ '$1 >= 128 {print $1"/"$2}' | sort -t/ -k1,1n -u | tr '\n' ' '; echo
