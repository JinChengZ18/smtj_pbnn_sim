#!/usr/bin/env python3
"""Post-process an Xschem-exported schematic SVG into a publication figure.

The raw `xschem --svg` export (eda/hero/schematics/<base>.svg) leaves a wide empty
canvas and no functional grouping. This step (run after build_schematics.sh):
  1. crops the SVG viewBox to the drawn content bounding box (removes whitespace);
  2. overlays colored DASHED rectangles that group the circuit into functional
     modules (input pair / latch / precharge / DAC / driver / cap-DAC ...), each
     with a small colored caption, to aid the reader -- outlines only, so nothing
     is occluded;
and writes article/figs/<article>.svg. Rasterise the PNG/PDF with WSL cairosvg
afterwards (Windows lacks libcairo). Run with Windows Python (pure text edit):

    python eda/hero/schematics/postprocess_schematic_svg.py <base>
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent.parent.parent / "article" / "figs"

# module-grouping boxes per schematic, in the SVG content coordinate system:
#   (x, y, w, h, color, caption)   caption drawn just above the box's top-left.
GROUPS = {
    "strongarm_sa": ("Chapter04_local_15", [
        (150, 88, 215, 170, "#5E3F8C", "cross-coupled latch"),
        (150, 290, 215, 72, "#1A6B5A", "input pair"),
        (205, 384, 95, 58, "#C77A0A", "clocked tail"),
    ]),
    # captions sit at each box's top-left in the box colour (module name beside box)
    "writepath": ("Chapter04_local_19", [
        (72, 66, 80, 254, "#5E3F8C", "R-string write-DAC"),
        (193, 184, 215, 70, "#1A6B5A", "k:1 tap select"),
        (468, 118, 82, 158, "#C77A0A", "CMOS write driver"),
        (578, 236, 96, 58, "#2c5aa0", "write-line IR"),
        (596, 306, 205, 142, "#A82038", "2T SOT-MTJ cell"),
    ]),
    "sar_readout": ("Chapter05_local_08", [
        (88, 100, 190, 66, "#1A6B5A", "column-shared input mux"),
        (300, 168, 268, 266, "#5E3F8C", "charge-redistribution cap-DAC"),
        (640, 176, 124, 88, "#C77A0A", "StrongARM comparator"),
    ]),
}

# original Xschem text labels to delete (now redrawn as coloured box captions)
REMOVE_TEXTS = {
    "writepath": ["voltage-mode resistor-string", "write-DAC (N matched taps)",
                  "k:1 tap select", "CMOS write driver", "write-line IR", "2T SOT-MTJ cell"],
    "sar_readout": ["column-shared", "input mux", "(time-mux)",
                    "charge-redistribution cap-DAC (binary-weighted, b bits)",
                    "StrongARM comparator"],
}

# ⑩ replace raw/vague in-figure formulas with the correct physical relation
TEXTREPL = {
    "writepath": [("D_row = D0 + dD(I_w, R_line)",
                   "V_head(r) = V_target + I_wr·R_par(r)")],
}

NUM = r"-?\d+\.?\d*"
# symbols whose ALL-CAPS form is a net/rail name, not a subscripted quantity
_NETS = {"VDD", "VSS", "GND", "VREF", "WWL", "RWL", "WRL", "RBL", "BL", "SL", "CLK"}


def subscriptize(svg: str) -> str:
    """Render `X_y` inside <text> as proper math subscripts (baseline-shift),
    so figures never show internal-variable underscores (publication norm)."""
    sub_re = re.compile(r"([A-Za-z0-9\)])_(\{)?([A-Za-z0-9]+)(\})?")

    def fix_text(m):
        head, body, tail = m.group(1), m.group(2), m.group(3)
        if "_" not in body or any(n in body for n in _NETS):
            return m.group(0)
        new = sub_re.sub(
            r'\1<tspan baseline-shift="sub" font-size="0.72em">\3</tspan>', body)
        return head + new + tail

    return re.sub(r"(<text\b[^>]*>)([^<]*)(</text>)", fix_text, svg)


def content_bbox(svg: str):
    xs, ys = [], []
    def add(x, y):
        xs.append(float(x)); ys.append(float(y))
    for m in re.finditer(r'<line[^>]*x1="(%s)"[^>]*y1="(%s)"[^>]*x2="(%s)"[^>]*y2="(%s)"' % (NUM, NUM, NUM, NUM), svg):
        add(m[1], m[2]); add(m[3], m[4])
    for m in re.finditer(r'<rect\b([^>]*?)/?>', svg):
        attrs = m[1]
        if 'l0' in attrs:                      # white full-canvas background
            continue
        g = {k: re.search(r'%s="(%s)"' % (k, NUM), attrs) for k in ("x", "y", "width", "height")}
        if not all(g.values()):
            continue
        x, y, w, h = (float(g[k][1]) for k in ("x", "y", "width", "height"))
        if w >= 700:                            # safety: skip any full-canvas rect
            continue
        add(x, y); add(x + w, y + h)
    for m in re.finditer(r'<circle[^>]*cx="(%s)"[^>]*cy="(%s)"[^>]*r="(%s)"' % (NUM, NUM, NUM), svg):
        cx, cy, r = map(float, m.groups()); add(cx - r, cy - r); add(cx + r, cy + r)
    for m in re.finditer(r'points="([^"]+)"', svg):
        nums = re.findall(NUM, m[1])
        for i in range(0, len(nums) - 1, 2):
            add(nums[i], nums[i + 1])
    for m in re.finditer(r'<path[^>]*\bd="([^"]+)"', svg):
        nums = re.findall(NUM, m[1])
        for i in range(0, len(nums) - 1, 2):
            add(nums[i], nums[i + 1])
    for m in re.finditer(r'translate\((%s),\s*(%s)\)' % (NUM, NUM), svg):
        x, y = float(m[1]), float(m[2])
        add(x, y); add(x, y - 7); add(x + 26, y)  # baseline -> cap height + label width
    return min(xs), min(ys), max(xs), max(ys)


def main(base):
    raw = (HERE / f"{base}.svg").read_text(encoding="utf-8")
    article, boxes = GROUPS[base]

    for old, new in TEXTREPL.get(base, []):
        if old not in raw:
            print(f"  WARN: text to replace not found: {old!r}")
        raw = raw.replace(old, new)
    for t in REMOVE_TEXTS.get(base, []):  # delete labels now redrawn as box captions
        raw, n = re.subn(r"<text\b[^>]*>" + re.escape(t) + r"</text>", "", raw)
        if n == 0:
            print(f"  WARN: remove-text not found: {t!r}")
    raw = subscriptize(raw)            # X_y -> proper subscript (no "_" in figures)

    minx, miny, maxx, maxy = content_bbox(raw)
    # include the group captions/boxes in the bbox so they are not clipped
    for x, y, w, h, _, cap in boxes:
        minx = min(minx, x); miny = min(miny, y - 12)
        maxx = max(maxx, x + w); maxy = max(maxy, y + h)
    pad = 10
    minx -= pad; miny -= pad; maxx += pad; maxy += pad
    vw, vh = round(maxx - minx, 2), round(maxy - miny, 2)

    # crop: replace the opening <svg ...> width/height and inject a viewBox
    raw = re.sub(r'(<svg\b[^>]*?)\swidth="[^"]*"\sheight="[^"]*"',
                 r'\1 width="%g" height="%g" viewBox="%g %g %g %g"' % (vw, vh, minx, miny, vw, vh),
                 raw, count=1)

    # build the module-box overlay
    ov = ['<g id="module-groups">']
    for x, y, w, h, col, cap in boxes:
        ov.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="none" '
                  f'stroke="{col}" stroke-width="1.4" stroke-dasharray="7 4" opacity="0.9"/>')
        if cap:
            ov.append(f'<text x="{x+3}" y="{y-3}" font-family="Helvetica,Arial,sans-serif" '
                      f'font-size="7.2" fill="{col}" font-weight="bold">{cap}</text>')
    ov.append('</g>')
    raw = raw.replace("</svg>", "\n".join(ov) + "\n</svg>")

    out = FIGS / f"{article}.svg"
    out.write_text(raw, encoding="utf-8")
    print(f"{base} -> {out.name}  viewBox=({minx:.0f},{miny:.0f},{vw:.0f},{vh:.0f})  +{len(boxes)} module boxes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "strongarm_sa")
