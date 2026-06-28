v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/res.sym} 150 160 0 0 {name=R1 value=R_u}
C {sym/res.sym} 150 250 0 0 {name=R2 value=R_u}
C {sym/res.sym} 150 340 0 0 {name=R3 value=R_u}
C {sym/res.sym} 150 430 0 0 {name=R4 value=R_u}
C {sym/nfet.sym} 300 325 0 0 {name=MTn model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 460 325 0 0 {name=MTp model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 620 250 0 0 {name=MDp model=sky130_fd_pr__pfet_01v8 W=8 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 620 360 0 0 {name=MDn model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/res.sym} 760 365 0 0 {name=Rline value=R_line}
C {sym/nfet.sym} 760 470 0 0 {name=MA model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/sot_mtj.sym} 880 540 0 0 {name=X1}
N 150 130 150 90 {}
N 150 190 150 220 {}
N 150 280 150 310 {}
N 150 370 150 400 {}
N 150 460 150 510 {}
N 150 295 320 295 {}
N 320 295 480 295 {}
N 320 355 480 355 {}
N 480 325 480 295 {}
N 480 355 560 355 {}
N 560 250 560 360 {}
N 560 250 600 250 {}
N 560 360 600 360 {}
N 640 220 640 180 {}
N 640 250 640 220 {}
N 640 360 640 390 {}
N 640 390 640 440 {}
N 640 280 640 330 {}
N 640 305 760 305 {}
N 760 305 760 335 {}
N 760 395 760 440 {}
N 760 440 780 440 {}
N 780 500 780 560 {}
N 780 560 840 560 {}
N 920 560 990 560 {}
N 880 500 880 460 {}
C {sym/ipin.sym} 150 90 0 1 {name=l1 lab=VREF}
C {sym/gnd.sym} 150 510 0 0 {name=l2 lab=VSS}
C {sym/vdd.sym} 640 180 0 0 {name=l3 lab=VDD}
C {sym/gnd.sym} 640 440 0 0 {name=l4 lab=VSS}
N 280 325 255 325 {}
C {sym/lab_pin.sym} 255 325 0 2 {name=l5 lab=sel}
N 440 325 415 325 {}
C {sym/lab_pin.sym} 415 325 0 2 {name=l6 lab=selb}
N 320 325 345 325 {}
C {sym/gnd.sym} 345 325 0 0 {name=l7 lab=VSS}
N 740 470 715 470 {}
C {sym/lab_pin.sym} 715 470 0 2 {name=l8 lab=WWL}
N 780 470 805 470 {}
C {sym/gnd.sym} 805 470 0 0 {name=l9 lab=VSS}
C {sym/opin.sym} 990 560 0 0 {name=l10 lab=SL}
C {sym/opin.sym} 880 460 0 1 {name=l11 lab=RD}
T {V_wdac} 360 380 0 0 0.22 0.22 {}
T {WRL} 680 293 0 0 0.22 0.22 {}
T {IR pre-distortion:  D_row = D0 + dD(I_w, R_line)} 330 95 0 0 0.26 0.26 {layer=7}
T {k:1 tap select} 320 250 0 0 0.26 0.26 {}
T {CMOS write driver} 540 112 0 0 0.3 0.3 {}
T {write-line IR} 790 415 0 0 0.24 0.24 {}
T {2T SOT-MTJ cell} 815 645 0 0 0.3 0.3 {}
T {voltage-mode resistor-string} 40 558 0 0 0.26 0.26 {}
T {write-DAC (N matched taps)} 40 578 0 0 0.26 0.26 {}
