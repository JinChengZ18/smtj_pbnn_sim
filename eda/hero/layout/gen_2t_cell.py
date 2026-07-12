#!/usr/bin/env python3
"""2T SOT-sMTJ cell layout (MTJ plan L1): sky130 PCell FETs + scripted straps
+ abstract BEOL black-box.

CMOS part (real sky130 layers; DRC target = 0 violations, sky130A_mr.drc):
  MW  nmos18 w=2.20 l=0.15  write access FET (I_wr = 0.9 V / 776 ohm ~ 1.16 mA)
  MR  nmos18 w=0.42 l=0.15  read access FET (minimum width), placed R180 so its
                            gate pad faces south (frees the north side for BEOL)
  ptap strip                body tie (tap/psdm/licon/li1/mcon/met1 "BODY" stub)
  scripted routing         mcon/met1/via1/met2/via2/met3 rectangles only -- the
                           PCell already brings S/D up to full-height li1 straps
                           and the gate to a licon'd li1 pad (npc included).

Stubs (cell-level, array assembly out of scope): WWL/RWL word-line met1 stubs,
WBL write-bitline met2 stub, SL source-line met2 stub, RBL read-bitline met1
stub, BODY met1 stub.

Abstract BEOL black-box (NOT manufacturable -- sky130A has no MRAM module;
layers 200/0 and 201/0 verified unused in sky130A.lyp + magic tech by
check_layers.sh, so Magic ignores them and CMOS extraction is unaffected):
  200/0  MTJ pillar envelope 0.08 um square   (public CD ~= 80 nm, Hikstor EDL
                                               2024, DOI 10.1109/LED.2024.3454609)
  201/0  SOT track 0.20 um wide               (public track width 200 nm)
Insertion level met2..met3: two met2 bottom-electrode pads (BE1 from the write
FET, BE2 = SL), public BE spacing 200 nm; met3 top-electrode pad over the
pillar feeds the read FET. The vertical BE->SOT and pillar->TE connections
exist only by declaration (annotation layers).

Run IN WSL (KLayout batch):
  klayout -b -r eda/hero/layout/gen_2t_cell.py
Env GEN2T_MODE=inventory dumps the PCell layer inventory instead.
"""
import json
import os
import sys

import pya

PCELL_DIR = "/opt/pdk/sky130A/libs.tech/klayout/pymacros"
sys.path.insert(0, PCELL_DIR)
from sky130_pcells import Sky130            # noqa: E402

Sky130()                                    # register PCell library "SKY130"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cell2t.gds")
SUMMARY = os.path.join(HERE, "cell2t_summary.json")
MODE = os.environ.get("GEN2T_MODE", "full")

ly = pya.Layout()
ly.dbu = 0.001
top = ly.create_cell("cell2t_smtj")

# ---- real sky130 GDS layers used by the scripted routing ----
L = {
    "tap":   (65, 44), "psdm": (94, 20),
    "licon": (66, 44), "li1":  (67, 20), "mcon": (67, 44),
    "met1":  (68, 20), "via1": (68, 44),
    "met2":  (69, 20), "via2": (69, 44),
    "met3":  (70, 20),
    # abstract black-box annotation layers (verified unused, check_layers.sh)
    "mtj_pillar": (200, 0), "sot_track": (201, 0),
}
LI = {k: ly.layer(*v) for k, v in L.items()}


def rect(layer_key, x1, y1, x2, y2):
    top.shapes(LI[layer_key]).insert(
        pya.Box(int(x1 / ly.dbu), int(y1 / ly.dbu), int(x2 / ly.dbu), int(y2 / ly.dbu)))


def place(pcell, w, trans):
    c = ly.create_cell(pcell, "SKY130", {"w": w, "l": 0.15, "nf": 1, "gr": 0})
    if c is None:
        raise RuntimeError(f"create_cell({pcell}) returned None")
    top.insert(pya.CellInstArray(c.cell_index(), trans))
    return c.bbox()


# ---- devices (gr=0: no per-device guard ring; body tie = shared ptap strip) ----
# MW at origin. Template geometry (from inventory run, w-independent x template):
#   diff (0,0)..(0.73,H) ; source li1 strap (0.01..0.28) ; drain strap (0.45..0.72)
#   gate li1 pad (0,H+0.22)..(0.73,H+0.83) ; free mcon slot (0.28,H+0.44)..(0.45,H+0.61)
place("nmos18", 2.20, pya.Trans(pya.Point(0, 0)))
# MR rotated 180 deg, displaced so its diff lands at (1.40,0)..(2.13,0.42):
#   R180 maps (x,y) -> (dx-x, dy-y); with dx=3.53, dy=0.42 the w=0.42 core
#   (diff (0,0)..(0.73,0.42)) lands at (2.80,0)..(3.53,0.42) -- shifted right for
#   nsdm spacing >= 0.38 from MW. Gate pad lands south at y -0.83..-0.22.
DX, DY = 3.53, 0.42
place("nmos18", 0.42, pya.Trans(2, False, pya.Point(int(DX / ly.dbu), int(DY / ly.dbu))))

top.flatten(-1, True)

if MODE == "inventory":
    print("== layer inventory ==")
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        n = top.shapes(li).size()
        if n:
            bb = top.bbox_per_layer(li)
            print(f"  {info.layer}/{info.datatype}: {n} shapes, "
                  f"({bb.left*ly.dbu:.3f},{bb.bottom*ly.dbu:.3f})..({bb.right*ly.dbu:.3f},{bb.top*ly.dbu:.3f})")
    for (l, d, tag) in [(67, 20, "li1"), (68, 20, "met1"), (67, 44, "mcon")]:
        li = ly.find_layer(pya.LayerInfo(l, d))
        print(f"  [{tag} {l}/{d}] rectangles:")
        for s in top.shapes(li).each():
            b = s.bbox()
            print(f"    ({b.left*ly.dbu:.3f},{b.bottom*ly.dbu:.3f})..({b.right*ly.dbu:.3f},{b.top*ly.dbu:.3f})")
    sys.exit(0)

# ---------------- scripted routing (all coords in um) ----------------
# gr=0 PCell already provides (inventory-verified):
#   MW: S/D li1 straps + FULL-HEIGHT met1 straps (0.00..0.29) / (0.44..0.73),
#       y -0.03..2.23, with mcon arrays; gate li1+met1 pad (0,2.42)..(0.73,3.03)
#       with 4 mcons.
#   MR (R180): strap met1 (2.799..3.089) / (3.239..3.529), y -0.03..0.45;
#       gate li1+met1 pad (2.799,-0.83)..(3.529,-0.22) with 4 mcons.
# So the scripted routing adds ONLY via1/met2/via2/met3 + met1 extensions.

# -- WBL: write bitline, met2 stub over MW source strap --
rect("via1", 0.07, 0.95, 0.22, 1.10)                      # on PCell met1 strap
rect("met2", 0.00, 0.60, 0.30, 2.40)                      # WBL stub

# -- MW drain -> BE1 pad (met2 trace from over-drain east to the black-box) --
rect("via1", 0.52, 1.815, 0.67, 1.965)                    # on PCell met1 strap
rect("met2", 0.45, 1.73, 1.30, 2.05)                      # trace + BE1 pad
# (WBL right edge 0.30 -> drain trace left edge 0.45: met2 spacing 0.15 >= 0.14)

# -- BE2 pad + SL stub (met2; public BE spacing 0.20) --
rect("met2", 1.50, 1.73, 1.82, 2.05)                      # BE2 pad
rect("met2", 1.50, 2.05, 1.82, 2.60)                      # SL stub north

# -- abstract black-box: SOT track over both BE pads, MTJ pillar mid-gap --
rect("sot_track", 0.98, 1.79, 1.82, 1.99)                 # 0.20 um wide track
rect("mtj_pillar", 1.36, 1.85, 1.44, 1.93)                # 0.08 um envelope

# -- TE: met3 pad over pillar + trace east to the read FET stack --
rect("met3", 1.15, 1.64, 1.65, 2.14)                      # TE pad (0.5 x 0.5)
rect("met3", 1.60, 1.68, 3.60, 2.08)                      # trace east (via2 encl >= 0.095)
# read FET east strap -> met1 north run directly above the strap -> stack
# (strap met1 is at 3.239..3.529 pre-snap; the 5-dbu snap below moves it to
#  3.240..3.530, so the extension uses the snapped coordinates)
rect("met1", 3.240, 0.35, 3.530, 2.30)                    # extend strap met1 north
rect("via1", 3.31, 1.80, 3.46, 1.95)
rect("met2", 3.20, 1.69, 3.60, 2.09)   # via2.5: m2 encl of via2 >=0.085 on 2 adjacent edges
rect("via2", 3.285, 1.775, 3.485, 1.975)
# (met3 trace covers the via2 with >=0.065 enclosure)

# -- RBL: read bitline = MR west strap met1 extended north --
rect("met1", 2.800, 0.35, 3.090, 1.40)

# -- WWL: MW gate word line, met1 stub west (gate pad is already li1+met1+mcon) --
rect("met1", -0.60, 2.42, 0.10, 3.03)

# -- RWL: MR gate word line (pad faces south), met1 stub east --
# (left edge 3.30 -> >=0.23 um overlap with the gate pad met1 (2.80..3.53);
#  an earlier 3.50 start left only 0.03 um overlap -- audit fix 2026-07-08)
rect("met1", 3.30, -0.72, 4.10, -0.33)

# -- ptap strip (body tie) west of MW --
rect("psdm", -1.495, 0.075, -0.835, 1.925)
rect("tap", -1.37, 0.20, -0.96, 1.80)
for y in (0.40, 0.80, 1.20):
    rect("licon", -1.25, y, -1.08, y + 0.17)
rect("li1", -1.34, 0.30, -0.99, 1.70)
rect("mcon", -1.25, 0.60, -1.08, 0.77)
rect("met1", -1.34, -0.20, -1.04, 0.90)                   # BODY pad + stub south

# ---- port labels (sky130 label datatypes: met1 68/5, met2 69/5, met3 70/5) ----
# Magic picks these up and emits a named-port subckt (enables LVS / testbench
# instantiation; audit fix 2026-07-08).
LBL = {"met1": ly.layer(68, 5), "met2": ly.layer(69, 5), "met3": ly.layer(70, 5)}


def label(layer_key, txt, x_um, y_um):
    top.shapes(LBL[layer_key]).insert(
        pya.Text(txt, pya.Trans(pya.Point(int(x_um / ly.dbu), int(y_um / ly.dbu)))))


label("met2", "WBL", 0.15, 1.50)
label("met2", "BE1", 1.14, 1.89)
label("met2", "SL", 1.66, 2.30)
label("met3", "TE", 1.40, 1.89)
label("met1", "RBL", 2.95, 1.20)
label("met1", "WWL", -0.40, 2.72)
label("met1", "RWL", 3.90, -0.52)
label("met1", "BODY", -1.19, -0.10)

# ---- 5-dbu (0.005 um) grid snap of ALL polygon layers ----
# (labels are Text objects on the */5 datatypes and are skipped by the
#  Region round-trip below: rebuild only layers that carry polygons)
# The sky130 KLayout PCell emits 0.001-um-offset shape edges at some widths
# (e.g. w=0.42), which the deck flags as *_OFFGRID; snapping every layer to the
# 0.005 um manufacturing grid restores compliance (uniform +-0.001 shifts, so
# template geometry and all designed margins are preserved).
for li in ly.layer_indexes():
    r = pya.Region(top.shapes(li))
    if r.is_empty():
        continue
    r.merge()
    r2 = r.snapped(5, 5)
    top.shapes(li).clear()
    top.shapes(li).insert(r2)

opt = pya.SaveLayoutOptions()
opt.gds2_write_timestamps = False        # byte-reproducible GDS (audit fix)
ly.write(OUT, opt)
bb = top.bbox()
w_um, h_um = bb.width() * ly.dbu, bb.height() * ly.dbu
area = w_um * h_um

# design bbox = union of drawn mask + black-box layers, EXCLUDING the PCell
# marker layer 235/4 (areaid, extends ~0.5 um beyond the drawn geometry)
dbb = pya.Box()
for li in ly.layer_indexes():
    info = ly.get_info(li)
    if (info.layer, info.datatype) == (235, 4):
        continue
    if top.shapes(li).size():
        dbb += top.bbox_per_layer(li)
dw_um, dh_um = dbb.width() * ly.dbu, dbb.height() * ly.dbu
darea = dw_um * dh_um

summary = {
    "gds": os.path.basename(OUT),
    "top_cell": "cell2t_smtj",
    "drawn_bbox_um": [round(bb.left * ly.dbu, 3), round(bb.bottom * ly.dbu, 3),
                      round(bb.right * ly.dbu, 3), round(bb.top * ly.dbu, 3)],
    "drawn_size_um": [round(w_um, 3), round(h_um, 3)],
    "drawn_area_um2": round(area, 3),
    "design_bbox_um": [round(dbb.left * ly.dbu, 3), round(dbb.bottom * ly.dbu, 3),
                       round(dbb.right * ly.dbu, 3), round(dbb.top * ly.dbu, 3)],
    "design_size_um": [round(dw_um, 3), round(dh_um, 3)],
    "design_area_um2": round(darea, 3),
    "estimate_area_um2": 4.6,
    "note": ("Drawn single-cell area includes cell-level stubs (WWL/RWL/WBL/SL/RBL/BODY) "
             "and a per-cell ptap strip; the 4.6 um^2 design-rule estimate assumes "
             "array-context amortization (shared taps, abutted routing). The drawn cell "
             "bounds the estimate from above; black-box layers 200/0, 201/0 are "
             "non-manufacturable annotations."),
    "pitch_candidates_um": {
        "x_drawn": round(w_um, 3),
        "y_drawn": round(h_um, 3),
        "sqrt_area_estimate": 2.145,
        "met1_5track_lower_bound": 1.7,
    },
    "blackbox": {"mtj_pillar_um": 0.08, "sot_track_w_um": 0.20,
                 "be_spacing_um": 0.20, "layers": {"mtj_pillar": "200/0", "sot_track": "201/0"},
                 "insertion": "met2 (BE pads / SL, couples with the met2+ write-line rule) "
                              "to met3 (TE pad / read line)"},
}
with open(SUMMARY, "w") as f:
    json.dump(summary, f, indent=1)

print("GDS_WRITTEN %s" % OUT)
print("drawn bbox: %.2f x %.2f um = %.2f um^2  (estimate 4.6 um^2, see note)"
      % (w_um, h_um, area))
print("summary -> %s" % SUMMARY)
