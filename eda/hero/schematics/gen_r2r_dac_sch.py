#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the R-2R LADDER write-DAC.

Topology is taken verbatim from net_r2r() in eda/hero/run_write_dac.py (the simulated 6-bit deck):

  ladder (R=400, 2R=800):
    Rterm  a1 0 800                              # 2R termination at the LSB end
    Rser_i a_i a_{i+1} 400   for i=1..nbits-1    # series-R rungs (a1 .. a6)
  per-bit 2R legs + CMOS transmission-gate switches (i=1..nbits, LSB..MSB):
    RL_i   a_i sw_i 800                          # 2R leg to the switch node
    TG_i:  src -> sw_i  with src = vref (bit=1) or gnd (bit=0)
           XTGn W=4 L=0.15 (gate=sel) , XTGp W=8 L=0.15 (gate=selb)
  output TG (idx 0): a_nbits -> bin  (MSB-end node to the high-Z buffer input)
  unity-gain Miller buffer (two-stage, PMOS input pair) drives the 776 ohm write load:
    bin -> [OTA in unity feedback] -> load , Rload=776

Drawn faithfully: every ladder/leg resistor and both FETs of every transmission gate are shown
(6 leg TGs + 1 output TG = 7 TGs = 14 FETs; 5 series-R + 1 term + 6 legs = 12 ladder resistors,
plus the 776 ohm load = 13 res). The two-stage Miller OTA is abstracted to the standard unity-
buffer triangle (sym/comp.sym) -- a journal figure shows the buffer as a block; its 7-transistor
internals live in the supplement netlist.

Component line format is  C {sym} x y ROT FLIP {attrs}  (ROT in {0,1,2,3}; res rot=1 -> horizontal,
pins P=+30,0 / M=-30,0). Local cleaned symbols only (sym/*). FET model sky130_fd_pr__{n,p}fet_01v8.
"""
import os

NFET, PFET, RES, COMP = "sym/nfet.sym", "sym/pfet.sym", "sym/res.sym", "sym/comp.sym"
NBITS = 6

# unrotated pin offsets (y down)
PIN = {
    "n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
    "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)},
    "rV": {"P": (0, -30), "M": (0, 30)},        # resistor rot=0 (vertical): P top, M bottom
    "rH": {"P": (30, 0), "M": (-30, 0)},        # resistor rot=1 (horizontal): P right, M left
}

# ----- compact geometry grid (y down) ----------------------------------------------------------
X0, DX = 120, 185                # first ladder node x, column pitch (a1..a6; DX>=180 so TGs clear)
RAIL_Y = 150                     # series-R rail
TERM_TOP_Y = 20                  # gnd terminator above a1
LEG_TOP_Y = RAIL_Y + 30          # 2R leg top
LEG_C_Y = RAIL_Y + 140           # 2R leg resistor center
SW_Y = RAIL_Y + 260              # switch node sw_i (leg bottom / TG top tie)
TG_Y = RAIL_Y + 395              # transmission-gate FET center row
SRC_Y = RAIL_Y + 545             # Vref/gnd source stub row
NODE_X = [X0 + i * DX for i in range(NBITS)]   # a1 .. a6


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    W = []
    nid = [0]

    def place(sym, x, y, rot, body, flip=0):
        o.append("C {%s} %d %d %d %d {%s}\n" % (sym, x, y, rot, flip, body))

    def fet(name, t, x, y, w):
        place(NFET if t == "n" else PFET, x, y, 0,
              "name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=0.15 nf=1 m=1" % (name, t, w))

    def resV(name, x, y, val):
        place(RES, x, y, 0, "name=%s value=%s" % (name, val))

    def resH(name, x, y, val):
        place(RES, x, y, 1, "name=%s value=%s" % (name, val))   # rot=1 -> horizontal

    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {sym/%s} %d %d %d 0 {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stub(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc
        ex, ey = px + vec[0], py + vec[1]
        if (ex, ey) != (px, py):
            W.append((px, py, ex, ey))
        lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.3, layer=None):
        tag = "{layer=%d}" % layer if layer else "{}"
        o.append("T {%s} %d %d 0 0 %g %g %s\n" % (s, x, y, size, size, tag))

    # ===================================================== R-2R LADDER ==========================
    # series-R rungs between a_i and a_{i+1} (horizontal, rot=1: P right=+30, M left=-30)
    for i in range(NBITS - 1):
        cx = (NODE_X[i] + NODE_X[i + 1]) // 2
        resH("Rser%d" % (i + 1), cx, RAIL_Y, "R")
        W.append((cx + 30, RAIL_Y, NODE_X[i + 1], RAIL_Y))   # P -> a_{i+1}
        W.append((cx - 30, RAIL_Y, NODE_X[i], RAIL_Y))       # M -> a_i

    # 2R termination at LSB end (a1) up to gnd
    resV("Rterm", NODE_X[0], (RAIL_Y + TERM_TOP_Y) // 2 + 0, "2R")
    tc = (RAIL_Y + TERM_TOP_Y) // 2
    W.append((NODE_X[0], RAIL_Y, NODE_X[0], tc + 30))        # a1 -> Rterm.M(bottom)
    W.append((NODE_X[0], tc - 30, NODE_X[0], TERM_TOP_Y))    # Rterm.P(top) -> gnd
    lab(NODE_X[0], TERM_TOP_Y, 1, "VSS", "gnd.sym")

    # ===================================================== 2R LEGS + TG SWITCHES ================
    out_x_list = []
    for i in range(NBITS):
        ax = NODE_X[i]
        resV("RL%d" % (i + 1), ax, LEG_C_Y, "2R")
        W.append((ax, RAIL_Y, ax, LEG_C_Y - 30))            # a_i -> leg P(top)
        W.append((ax, LEG_C_Y + 30, ax, SW_Y))              # leg M(bottom) -> sw_i

        # transmission gate: nfet (left of axis) + pfet (right of axis), kept narrow so the
        # inter-slice gap stays clear for the bit-control labels.
        nx, px = ax - 45, ax + 45
        fet("MN%d" % (i + 1), "n", nx, TG_Y, 4)
        fet("MP%d" % (i + 1), "p", px, TG_Y, 8)
        nD = (nx + 20, TG_Y - 30); nS = (nx + 20, TG_Y + 30)
        pS = (px + 20, TG_Y - 30); pD = (px + 20, TG_Y + 30)
        topy, boty = TG_Y - 55, TG_Y + 55
        # top tie (-> sw_i)
        W.append((nD[0], nD[1], nD[0], topy)); W.append((pS[0], pS[1], pS[0], topy))
        W.append((nD[0], topy, pS[0], topy))
        W.append((ax, SW_Y, ax, topy))                       # leg drop lands on top tie
        # bottom tie (-> src)
        W.append((nS[0], nS[1], nS[0], boty)); W.append((pD[0], pD[1], pD[0], boty))
        W.append((nS[0], boty, pD[0], boty))
        W.append((ax, boty, ax, SRC_Y))                      # bottom tie -> src stub (on axis)
        lab(ax, SRC_Y, 0, "Vref/0", "lab_pin.sym")
        # bit controls: nfet gate=b{i} (left), pfet gate=b{i}b routed up-and-left so its label sits
        # ABOVE the slice (clear of the next slice's nfet gate in the inter-slice gap).
        ngx = nx - 20
        stub((ngx, TG_Y), (-25, 0), 2, "b%d" % i)            # nfet gate -> b{i}
        pgx = px - 20
        gy = TG_Y - 45
        W.append((pgx, TG_Y, pgx, gy)); W.append((pgx, gy, ngx - 25, gy))   # pfet gate up & left
        lab(ngx - 25, gy, 2, "b%db" % i)                     # b{i}b label, stacked above b{i}
        stub((px + 20, TG_Y), (22, 0), 0, "VDD", "vdd.sym")  # pfet bulk -> VDD

    # ===================================================== OUTPUT TG + BUFFER ===================
    # Stacked vertically below the MSB end (a6) so the figure stays compact in width and tall in
    # height (matching the canvas aspect): a6 -> output TG -> bin -> unity buffer -> 776 ohm load.
    a6x = NODE_X[-1]
    otg_x = a6x + 120
    oN, oP = otg_x - 30, otg_x + 30
    oy = RAIL_Y + 90
    fet("MNo", "n", oN, oy, 4)
    fet("MPo", "p", oP, oy, 8)
    nD = (oN + 20, oy - 30); nS = (oN + 20, oy + 30)
    pS = (oP + 20, oy - 30); pD = (oP + 20, oy + 30)
    topy, boty = oy - 55, oy + 55
    W.append((nD[0], nD[1], nD[0], topy)); W.append((pS[0], pS[1], pS[0], topy))
    W.append((nD[0], topy, pS[0], topy))
    W.append((nS[0], nS[1], nS[0], boty)); W.append((pD[0], pD[1], pD[0], boty))
    W.append((nS[0], boty, pD[0], boty))
    # a6 -> across -> down into output-TG top tie
    in_x = nD[0]
    W.append((a6x, RAIL_Y, in_x, RAIL_Y)); W.append((in_x, RAIL_Y, in_x, topy))
    stub((oN - 20, oy), (-22, 0), 2, "en")
    stub((oP - 20, oy), (-22, 0), 2, "enb")
    stub((oP + 20, oy), (22, 0), 0, "VDD", "vdd.sym")
    # bottom tie -> bin -> buffer input (buffer placed BELOW, to the right)
    bin_x = (nS[0] + pD[0]) // 2
    buf_x = otg_x + 80
    buf_y = boty + 150
    place(COMP, buf_x, buf_y, 0, "name=XBUF")
    inp = (buf_x - 40, buf_y - 15); inn = (buf_x - 40, buf_y + 15); out = (buf_x + 45, buf_y)
    W.append((bin_x, boty, bin_x, inp[1])); W.append((bin_x, inp[1], inp[0], inp[1]))
    txt("bin", bin_x + 8, boty + 45, 0.20)
    # unity feedback OUT -> INN (loop tucked under the triangle)
    fb_x, fb_y = buf_x + 70, buf_y + 75
    W.append((out[0], out[1], fb_x, out[1]))
    W.append((fb_x, out[1], fb_x, fb_y))
    W.append((fb_x, fb_y, inn[0] - 25, fb_y))
    W.append((inn[0] - 25, fb_y, inn[0] - 25, inn[1]))
    W.append((inn[0] - 25, inn[1], inn[0], inn[1]))
    # OUT node -> Vload tap -> 776 ohm load DOWN to gnd (load stacked below to save width)
    tap_x = fb_x + 70
    rl_c = out[1] + 100
    resV("Rload", tap_x, rl_c, "776")
    W.append((out[0], out[1], tap_x, out[1]))
    W.append((tap_x, out[1], tap_x, rl_c - 30))         # OUT/Vload -> Rload.P(top)
    W.append((tap_x, rl_c + 30, tap_x, rl_c + 70))      # Rload.M(bottom) -> gnd
    lab(tap_x, rl_c + 70, 0, "VSS", "gnd.sym")
    stub((tap_x, out[1]), (45, 0), 0, "Vload", "opin.sym")
    load_x = tap_x
    # (comp.sym is the abstracted unity buffer block; its rails/internals are in the supplement
    #  netlist, so no power-pin stubs are drawn on the triangle -- keeps the block uncluttered.)

    # emit wires
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    # ===================================================== ANNOTATIONS ==========================
    # (module-group titles are redrawn as colored dashed box captions by postprocess; not in-schematic)
    # ladder node names a1..a6 (functional labels, kept)
    for i in range(NBITS):
        txt("a%d" % (i + 1), NODE_X[i] + 8, RAIL_Y - 8, 0.20)

    # ---- normalize: center content in xschem's fixed headless SVG viewport ---------------------
    # The build (xschem -q --svg) maps world->SVG by  svg = 0.55*world + (~0.3, ~214) into a fixed
    # 900x503 canvas, i.e. the visible world window is ~x[-0.5,1636] y[-389,525] (center ~818,68).
    # We translate all geometry so the content bbox center lands on that window center -> the figure
    # fills the frame with symmetric margins (no large top/bottom whitespace).
    import re as _re
    lines = "".join(o).splitlines(keepends=True)
    xs, ys = [], []
    for ln in lines:
        if ln.startswith("N "):
            a = ln.split(); xs += [int(a[1]), int(a[3])]; ys += [int(a[2]), int(a[4])]
        else:
            m = _re.match(r"[CT] \{.*?\} (-?\d+) (-?\d+)", ln)
            if m:
                xs.append(int(m.group(1))); ys.append(int(m.group(2)))
    cx0, cy0 = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    # world-center that maps to the canvas center under xschem's fixed headless transform
    # (calibrated: svg = 0.577*world + (-48.5, 293.9) into a 900x503 canvas).
    WIN_CX, WIN_CY = 863, -75
    dx, dy = int(round(WIN_CX - cx0)), int(round(WIN_CY - cy0))

    def shift_line(ln):
        if ln.startswith("N "):
            a = ln.split()
            return "N %d %d %d %d {}\n" % (int(a[1]) + dx, int(a[2]) + dy,
                                           int(a[3]) + dx, int(a[4]) + dy)
        m = _re.match(r"([CT]) (\{.*?\}) (-?\d+) (-?\d+)(.*)", ln, _re.S)
        if m:
            return "%s %s %d %d%s" % (m.group(1), m.group(2), int(m.group(3)) + dx,
                                      int(m.group(4)) + dy, m.group(5))
        return ln

    out_lines = [shift_line(ln) for ln in lines]

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "r2r_dac.sch"), "w").write("".join(out_lines))
    print("wrote r2r_dac.sch (%d nfet, %d pfet, %d res, 1 buffer-block); "
          "content %dx%d centered (dx=%d dy=%d)"
          % (NBITS + 1, NBITS + 1, (NBITS - 1) + 1 + NBITS + 1,
             max(xs) - min(xs), max(ys) - min(ys), dx, dy))


if __name__ == "__main__":
    main()
