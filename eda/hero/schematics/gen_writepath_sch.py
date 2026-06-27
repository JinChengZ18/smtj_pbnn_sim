#!/usr/bin/env python3
"""Generate a compact, journal-style Xschem schematic for the WRITE PATH.

Topology (matches the selected design in run_write_dac.py / ir_aware_writedac.py / run_write_driver.sh):
  voltage-mode resistor-string DAC  ->  transmission-gate tap select (k-of-N decode)  ->
  CMOS push-pull write driver  ->  write line with series IR resistance R_line  ->
  2T SOT-MTJ cell (access nFET + 3-terminal SOT-MTJ; read terminal broken out to the sense amp).

The resistor string is drawn with 4 matched unit elements + an "N matched taps" annotation (a fully
drawn 32-tap ladder defeats compactness); the selected tap is routed through a real CMOS transmission
gate. Devices use local cleaned symbols (sym/nfet.sym, sym/pfet.sym, sym/res.sym, sym/sot_mtj.sym).
"""
import os

NFET, PFET, RES, SOT = "sym/nfet.sym", "sym/pfet.sym", "sym/res.sym", "sym/sot_mtj.sym"
P = {"n": {"D": (20, -30), "G": (-20, 0), "S": (20, 30), "B": (20, 0)},
     "p": {"S": (20, -30), "G": (-20, 0), "D": (20, 30), "B": (20, 0)},
     "r": {"P": (0, -30), "M": (0, 30)},
     "sot": {"Tin": (-40, 20), "Tsl": (40, 20), "Trd": (0, -40)}}

# (name, type, x, y)  -- y increases downward
DEV = [
    ("R1", "r", 150, 160), ("R2", "r", 150, 250), ("R3", "r", 150, 340), ("R4", "r", 150, 430),
    ("MTn", "n", 300, 325), ("MTp", "p", 460, 325),          # transmission-gate tap select
    ("MDp", "p", 620, 250), ("MDn", "n", 620, 360),          # CMOS push-pull write driver
    ("Rline", "r", 760, 365),                                # write-line series IR resistance
    ("MA", "n", 760, 470),                                   # access nFET (write word line)
    ("X1", "sot", 880, 540),                                 # 3-terminal SOT-MTJ
]
DT = {n: t for n, t, *_ in DEV}
XY = {n: (x, y) for n, t, x, y in DEV}
SIZE = {"MTn": (1.0, 0.15), "MTp": (2.0, 0.15), "MDp": (8.0, 0.15),
        "MDn": (4.0, 0.15), "MA": (2.0, 0.15)}


def pin(n, p):
    x, y = XY[n]; dx, dy = P[DT[n]][p]; return x + dx, y + dy


def main():
    o = ["v {xschem version=3.4.4 file_version=1.2}\nG {}\nK {}\nV {}\nS {}\nE {}\n"]
    for n, t, x, y in DEV:
        if t in ("n", "p"):
            w, l = SIZE[n]
            o.append("C {%s} %d %d 0 0 {name=%s model=sky130_fd_pr__%sfet_01v8 W=%g L=%g nf=1 m=1}\n"
                     % (NFET if t == "n" else PFET, x, y, n, t, w, l))
        elif t == "r":
            val = "R_line" if n == "Rline" else "R_u"
            o.append("C {%s} %d %d 0 0 {name=%s value=%s}\n" % (RES, x, y, n, val))
        elif t == "sot":
            o.append("C {%s} %d %d 0 0 {name=%s}\n" % (SOT, x, y, n))

    W = []
    # --- resistor string: VREF -> R1 -> R2 -> R3 -> R4 -> VSS ---
    W += [(150, 130, 150, 90)]                                       # R1.P -> VREF
    W += [(150, 190, 150, 220), (150, 280, 150, 310), (150, 370, 150, 400)]  # junctions
    W += [(150, 460, 150, 510)]                                      # R4.M -> VSS
    # --- selected tap (between R2,R3) -> CMOS transmission gate ---
    W += [(150, 295, 320, 295), (320, 295, 480, 295)]               # tap -> MTn.D, MTp.S
    W += [(320, 355, 480, 355)]                                      # V_wdac = MTn.S = MTp.D
    W += [(480, 325, 480, 295)]                                      # MTp bulk -> source
    # --- V_wdac -> driver input bus -> both driver gates ---
    W += [(480, 355, 560, 355), (560, 250, 560, 360),
          (560, 250, 600, 250), (560, 360, 600, 360)]
    # --- CMOS driver: rails, bulks, output node WRL ---
    W += [(640, 220, 640, 180), (640, 250, 640, 220)]               # MDp.S->VDD, MDp.B->S
    W += [(640, 360, 640, 390), (640, 390, 640, 440)]               # MDn.B->S, MDn.S->VSS
    W += [(640, 280, 640, 330), (640, 305, 760, 305)]               # WRL node + run to write line
    # --- write line: WRL -> R_line -> access drain ---
    W += [(760, 305, 760, 335)]                                      # WRL -> Rline.P
    W += [(760, 395, 760, 440), (760, 440, 780, 440)]               # Rline.M -> MA.D
    # --- access nFET source -> SOT-MTJ Tin ---
    W += [(780, 500, 780, 560), (780, 560, 840, 560)]
    # --- SOT-MTJ terminals ---
    W += [(920, 560, 990, 560)]                                      # Tsl -> SL
    W += [(880, 500, 880, 460)]                                      # Trd -> readout
    for seg in W:
        o.append("N %d %d %d %d {}\n" % seg)

    nid = [0]
    def lab(px, py, rot, name, sym="lab_pin.sym"):
        nid[0] += 1
        o.append("C {devices/%s} %d %d 0 %d {name=l%d lab=%s}\n" % (sym, px, py, rot, nid[0], name))

    def stublab(pc, vec, rot, name, sym="lab_pin.sym"):
        px, py = pc; ex, ey = px + vec[0], py + vec[1]
        o.append("N %d %d %d %d {}\n" % (px, py, ex, ey)); lab(ex, ey, rot, name, sym)

    def txt(s, x, y, size=0.3):
        o.append("T {%s} %d %d 0 0 %g %g {}\n" % (s, x, y, size, size))

    # rails / references (compact supply symbols, not large text labels)
    lab(150, 90, 1, "VREF", "ipin.sym")
    lab(150, 510, 0, "VSS", "gnd.sym")
    lab(640, 180, 0, "VDD", "vdd.sym")
    lab(640, 440, 0, "VSS", "gnd.sym")
    # transmission-gate controls + body
    stublab(pin("MTn", "G"), (-25, 0), 2, "sel")
    stublab(pin("MTp", "G"), (-25, 0), 2, "selb")
    stublab(pin("MTn", "B"), (25, 0), 0, "VSS", "gnd.sym")
    # cell controls / body / terminals
    stublab(pin("MA", "G"), (-25, 0), 2, "WWL")
    stublab(pin("MA", "B"), (25, 0), 0, "VSS", "gnd.sym")
    lab(990, 560, 0, "SL", "opin.sym")
    lab(880, 460, 1, "RD", "opin.sym")
    # internal node names (text, single nets -- no port symbol needed)
    txt("V_wdac", 360, 380, 0.22)
    txt("WRL", 680, 293, 0.22)
    # functional group annotations (concise; the full caption lives in the supplement)
    txt("IR pre-distortion:  D_row = D0 + dD(I_w, R_line)", 330, 95, 0.26)
    txt("k:1 tap select", 320, 250, 0.26)
    txt("CMOS write driver", 540, 112)
    txt("write-line IR", 790, 415, 0.24)
    txt("2T SOT-MTJ cell", 815, 645)
    txt("voltage-mode resistor-string", 40, 558, 0.26)
    txt("write-DAC (N matched taps)", 40, 578, 0.26)

    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, "writepath.sch"), "w").write("".join(o))
    print("wrote writepath.sch (%d devices)" % len(DEV))


if __name__ == "__main__":
    main()
