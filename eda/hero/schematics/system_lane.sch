v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/pfet.sym} 320 360 0 0 {name=MDp model=sky130_fd_pr__pfet_01v8 W=8 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 320 460 0 0 {name=MDn model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 560 420 0 1 {name=MW model=sky130_fd_pr__nfet_01v8 W=3 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 680 330 0 0 {name=MR model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/sot_mtj.sym} 700 420 0 0 {name=X1}
C {sym/res.sym} 700 250 0 0 {name=Rti value=R_TI}
C {sym/comp.sym} 920 320 0 0 {name=CMP}
N 240 420 280 420 {}
N 280 360 280 460 {}
N 280 360 300 360 {}
N 280 460 300 460 {}
N 340 330 340 300 {}
N 340 360 340 330 {}
N 340 460 340 490 {}
N 340 490 340 520 {}
N 340 390 340 430 {}
N 340 430 340 440 {}
N 340 440 530 440 {}
N 590 440 660 440 {}
N 740 440 740 560 {}
N 700 360 700 380 {}
N 700 300 700 280 {}
N 700 220 700 190 {}
N 700 300 880 300 {}
N 880 300 880 305 {}
N 820 300 820 450 {}
N 965 320 1000 320 {}
L 4 80 380 240 380 {}
L 4 240 380 240 460 {}
L 4 240 460 80 460 {}
L 4 80 460 80 380 {}
L 4 790 450 1030 450 {}
L 4 1030 450 1030 570 {}
L 4 1030 570 790 570 {}
L 4 790 570 790 450 {}
N 790 530 750 530 {}
N 1030 520 1065 520 {}
C {devices/vdd.sym} 340 300 0 0 {name=l1 lab=VDD}
C {devices/gnd.sym} 340 520 0 0 {name=l2 lab=GND}
C {devices/ipin.sym} 700 190 0 1 {name=l3 lab=VREF}
N 560 440 560 465 {}
C {devices/gnd.sym} 560 465 0 0 {name=l4 lab=GND}
N 700 330 745 330 {}
C {devices/gnd.sym} 745 330 0 0 {name=l5 lab=GND}
N 880 335 840 335 {}
C {devices/ipin.sym} 840 335 0 2 {name=l6 lab=VCM}
C {devices/lab_pin.sym} 740 560 0 0 {name=l7 lab=SL}
N 560 400 560 360 {}
C {devices/ipin.sym} 560 360 0 1 {name=l8 lab=WWL}
N 660 330 605 330 {}
C {devices/ipin.sym} 605 330 0 2 {name=l9 lab=RWL}
C {devices/opin.sym} 1000 320 0 0 {name=l10 lab=p_out}
C {devices/ipin.sym} 750 530 0 2 {name=l11 lab=CLK}
C {devices/opin.sym} 1065 520 0 0 {name=l12 lab=rc}
T {BL} 440 428 0 0 0.22 0.22 {}
T {RBL} 716 306 0 0 0.22 0.22 {}
T {write-DAC} 110 412 0 0 0.26 0.26 {}
T {R-string + IR} 96 436 0 0 0.22 0.22 {}
T {column-shared SAR} 830 505 0 0 0.28 0.28 {}
T {(reservoir read-out)} 835 532 0 0 0.22 0.22 {}
T {CMOS write driver} 250 300 0 0 0.26 0.26 {}
T {2T SOT-MTJ cell} 600 490 0 0 0.26 0.26 {}
T {R_TI (TIA)} 724 248 0 0 0.24 0.24 {}
T {StrongARM comparator} 855 250 0 0 0.26 0.26 {}
T {(p-bit read-out)} 875 274 0 0 0.22 0.22 {}
T {sMTJ p-bit / reservoir compute lane} 360 110 0 0 0.34 0.34 {}
T {x N rows (shared BL / SL / RBL)   .   x M columns (WWL / RWL shared; SAR shared across columns)} 180 620 0 0 0.24 0.24 {}
