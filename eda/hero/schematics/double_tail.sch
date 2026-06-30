v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/pfet.sym} 210 230 0 0 {name=Mpc1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 390 230 0 0 {name=Mpc2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 210 470 0 0 {name=Min1 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 390 470 0 0 {name=Min2 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 300 660 0 0 {name=Mt1 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 640 230 0 0 {name=Mcp1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 790 230 0 0 {name=Mpo2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 970 230 0 0 {name=Mpo1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1120 230 0 0 {name=Mcp2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 640 470 0 0 {name=Ml1 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 790 470 0 0 {name=Mcn1 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 970 470 0 0 {name=Mcn2 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1120 470 0 0 {name=Ml2 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 880 660 0 0 {name=Mt2 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
N 150 110 1180 110 {}
N 280 820 920 820 {}
N 230 200 230 110 {}
N 410 200 410 110 {}
N 660 200 660 110 {}
N 810 200 810 110 {}
N 990 200 990 110 {}
N 1140 200 1140 110 {}
N 230 260 230 440 {}
N 410 260 410 440 {}
N 230 500 230 600 {}
N 410 500 410 600 {}
N 230 600 410 600 {}
N 320 600 320 630 {}
N 320 690 320 820 {}
N 660 260 660 320 {}
N 810 260 810 320 {}
N 660 320 810 320 {}
N 660 440 660 380 {}
N 810 440 810 380 {}
N 660 380 810 380 {}
N 810 320 810 380 {}
N 990 260 990 320 {}
N 1140 260 1140 320 {}
N 990 320 1140 320 {}
N 990 440 990 380 {}
N 1140 440 1140 380 {}
N 990 380 1140 380 {}
N 990 320 990 380 {}
N 660 500 660 600 {}
N 810 500 810 600 {}
N 990 500 990 600 {}
N 1140 500 1140 600 {}
N 660 600 1140 600 {}
N 900 600 900 630 {}
N 900 690 900 820 {}
N 280 660 250 660 {}
C {sym/lab_pin.sym} 250 660 0 2 {name=l1 lab=clk}
N 860 660 830 660 {}
C {sym/lab_pin.sym} 830 660 0 2 {name=l2 lab=clk}
N 190 230 160 230 {}
C {sym/lab_pin.sym} 160 230 0 2 {name=l3 lab=clk}
N 370 230 340 230 {}
C {sym/lab_pin.sym} 340 230 0 2 {name=l4 lab=clk}
N 770 230 740 230 {}
C {sym/lab_pin.sym} 740 230 0 2 {name=l5 lab=clk}
N 950 230 920 230 {}
C {sym/lab_pin.sym} 920 230 0 2 {name=l6 lab=clk}
N 770 470 740 470 {}
C {sym/lab_pin.sym} 740 470 0 2 {name=l7 lab=outp}
N 950 470 920 470 {}
C {sym/lab_pin.sym} 920 470 0 2 {name=l8 lab=outn}
N 620 230 590 230 {}
C {sym/lab_pin.sym} 590 230 0 2 {name=l9 lab=outp}
N 1100 230 1070 230 {}
C {sym/lab_pin.sym} 1070 230 0 2 {name=l10 lab=outn}
N 620 470 590 470 {}
C {sym/lab_pin.sym} 590 470 0 2 {name=l11 lab=di}
N 1100 470 1070 470 {}
C {sym/lab_pin.sym} 1070 470 0 2 {name=l12 lab=dib}
N 190 470 160 470 {}
C {sym/ipin.sym} 160 470 0 2 {name=l13 lab=vinp}
N 370 470 340 470 {}
C {sym/ipin.sym} 340 470 0 2 {name=l14 lab=vinn}
C {sym/lab_pin.sym} 230 350 0 0 {name=l15 lab=di}
C {sym/lab_pin.sym} 410 350 0 0 {name=l16 lab=dib}
C {sym/opin.sym} 810 295 0 1 {name=l17 lab=outn}
C {sym/opin.sym} 990 295 0 1 {name=l18 lab=outp}
N 810 320 810 295 {}
N 990 320 990 295 {}
N 230 470 255 470 {}
C {sym/gnd.sym} 255 470 0 0 {name=l19 lab=VSS}
N 410 470 435 470 {}
C {sym/gnd.sym} 435 470 0 0 {name=l20 lab=VSS}
N 660 470 685 470 {}
C {sym/gnd.sym} 685 470 0 0 {name=l21 lab=VSS}
N 810 470 835 470 {}
C {sym/gnd.sym} 835 470 0 0 {name=l22 lab=VSS}
N 990 470 1015 470 {}
C {sym/gnd.sym} 1015 470 0 0 {name=l23 lab=VSS}
N 1140 470 1165 470 {}
C {sym/gnd.sym} 1165 470 0 0 {name=l24 lab=VSS}
N 320 660 345 660 {}
C {sym/gnd.sym} 345 660 0 0 {name=l25 lab=VSS}
N 900 660 925 660 {}
C {sym/gnd.sym} 925 660 0 0 {name=l26 lab=VSS}
N 230 230 230 200 {}
N 410 230 410 200 {}
N 660 230 660 200 {}
N 810 230 810 200 {}
N 990 230 990 200 {}
N 1140 230 1140 200 {}
N 150 110 150 82 {}
C {sym/vdd.sym} 150 82 0 1 {name=l27 lab=VDD}
N 320 820 320 848 {}
C {sym/gnd.sym} 320 848 0 3 {name=l28 lab=VSS}
