#!/bin/bash
# Export Xschem .sch -> PNG/SVG/PDF headless via the WSLg X server (DISPLAY=:0).
# Timeout-guarded so a stray interactive xschem can never hang (lesson learned: always -q + timeout).
#   wsl -d Ubuntu-24.04-EDA -- bash -lc 'cd "<repo>/eda/hero/schematics" && bash build_schematics.sh strongarm_sa.sch'
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
RC="$DIR/xschemrc"   # local rc: sources sky130 rc + adds local cleaned symbols (sym/)
export DISPLAY=:0
cd "$DIR"
for sch in "$@"; do
  base="${sch%.sch}"
  for fmt in png svg pdf; do
    timeout 90 xschem --rcfile "$RC" --tcl "set dark_colorscheme 0" -q --"$fmt" --plotfile "$DIR/$base.$fmt" "$DIR/$sch" </dev/null >/dev/null 2>&1
    rc=$?
    [ "$rc" -eq 124 ] && echo "  $base.$fmt: TIMEOUT (killed)" && continue
  done
  png_sz=$(wc -c < "$base.png" 2>/dev/null || echo 0)
  echo "$base -> png ${png_sz}B, svg $([ -f "$base.svg" ] && echo ok || echo -), pdf $([ -f "$base.pdf" ] && echo ok || echo -)"
done
