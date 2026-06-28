v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/nfet.sym} 160 110 0 0 {name=MS0 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 280 110 0 0 {name=MS1 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/cap.sym} 420 240 0 0 {name=C2 value=4C}
C {sym/cap.sym} 540 240 0 0 {name=C1 value=2C}
C {sym/cap.sym} 660 240 0 0 {name=C0 value=C}
C {sym/sw.sym} 420 330 0 0 {name=b2}
C {sym/sw.sym} 540 330 0 0 {name=b1}
C {sym/sw.sym} 660 330 0 0 {name=b0}
C {sym/comp.sym} 880 210 0 0 {name=CMP}
N 180 50 180 80 {}
N 180 140 180 180 {}
N 300 50 300 80 {}
N 300 140 300 180 {}
N 180 180 760 180 {}
N 420 180 420 210 {}
N 540 180 540 210 {}
N 660 180 660 210 {}
N 420 270 420 305 {}
N 540 270 540 305 {}
N 660 270 660 305 {}
N 408 355 408 400 {}
N 432 355 432 445 {}
N 528 355 528 400 {}
N 552 355 552 445 {}
N 648 355 648 400 {}
N 672 355 672 445 {}
N 404 400 720 400 {}
N 404 445 700 445 {}
N 760 180 820 180 {}
N 820 180 820 195 {}
N 820 195 840 195 {}
N 925 210 925 300 {}
L 4 860 300 1010 300 {}
L 4 1010 300 1010 430 {}
L 4 1010 430 860 430 {}
L 4 860 430 860 300 {}
N 860 330 820 330 {}
N 1010 360 1055 360 {}
N 860 400 820 400 {}
C {sym/ipin.sym} 180 50 0 1 {name=l1 lab=col0}
C {sym/ipin.sym} 300 50 0 1 {name=l2 lab=col1}
N 140 110 115 110 {}
C {sym/lab_pin.sym} 115 110 0 2 {name=l3 lab=sel0}
N 260 110 235 110 {}
C {sym/lab_pin.sym} 235 110 0 2 {name=l4 lab=sel1}
N 180 110 205 110 {}
C {sym/gnd.sym} 205 110 0 0 {name=l5 lab=GND}
N 300 110 325 110 {}
C {sym/gnd.sym} 325 110 0 0 {name=l6 lab=GND}
C {sym/lab_pin.sym} 720 400 0 0 {name=l7 lab=VREF}
C {sym/gnd.sym} 700 445 0 0 {name=l8 lab=GND}
N 840 225 800 225 {}
C {sym/ipin.sym} 800 225 0 2 {name=l9 lab=VCM}
C {sym/ipin.sym} 820 330 0 2 {name=l10 lab=CLK}
C {sym/opin.sym} 1055 360 0 0 {name=l11 lab=Dout}
C {sym/lab_pin.sym} 820 400 0 2 {name=l12 lab=b[2:0]}
T {Vx} 470 168 0 0 0.22 0.22 {}
T {cmp} 935 250 0 0 0.22 0.22 {}
T {SAR logic} 888 360 0 0 0.3 0.3 {}
T {column-shared} 20 22 0 0 0.26 0.26 {}
T {input mux} 20 44 0 0 0.26 0.26 {}
T {(time-mux)} 20 66 0 0 0.24 0.24 {}
T {charge-redistribution cap-DAC (binary-weighted, b bits)} 380 132 0 0 0.26 0.26 {}
T {ref switches: VREF / GND per bit} 410 490 0 0 0.24 0.24 {}
T {StrongARM comparator} 820 120 0 0 0.28 0.28 {}
T {-> shared comparator + DAC amortised across columns} 470 540 0 0 0.24 0.24 {layer=7}
