v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/pfet.sym} 360 210 0 0 {name=S1p1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 590 210 0 0 {name=S1p2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 200 210 0 0 {name=S1pr1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 750 210 0 0 {name=S1pr2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 360 380 0 0 {name=S1n1 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 590 380 0 0 {name=S1n2 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 200 380 0 0 {name=S1prd1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 750 380 0 0 {name=S1prd2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 360 540 0 0 {name=S1in1 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 590 540 0 0 {name=S1in2 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 475 670 0 0 {name=S1tail model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1010 210 0 0 {name=S2p1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1240 210 0 0 {name=S2p2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 850 210 0 0 {name=S2pr1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1400 210 0 0 {name=S2pr2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1010 380 0 0 {name=S2n1 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1240 380 0 0 {name=S2n2 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 850 380 0 0 {name=S2prd1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1400 380 0 0 {name=S2prd2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1010 540 0 0 {name=S2in1 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1240 540 0 0 {name=S2in2 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1125 670 0 0 {name=S2tail model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/lab_pin.sym} 312 210 0 2 {name=l1 lab=s1p}
C {sym/lab_pin.sym} 312 380 0 2 {name=l2 lab=s1p}
C {sym/lab_pin.sym} 542 210 0 2 {name=l3 lab=s1n}
C {sym/lab_pin.sym} 542 380 0 2 {name=l4 lab=s1n}
C {sym/lab_pin.sym} 152 210 0 2 {name=l5 lab=clk}
C {sym/lab_pin.sym} 152 380 0 2 {name=l6 lab=clk}
C {sym/lab_pin.sym} 702 210 0 2 {name=l7 lab=clk}
C {sym/lab_pin.sym} 702 380 0 2 {name=l8 lab=clk}
C {sym/lab_pin.sym} 427 670 0 2 {name=l9 lab=clk}
C {sym/gnd.sym} 404 380 0 0 {name=l10 lab=VSS}
C {sym/gnd.sym} 634 380 0 0 {name=l11 lab=VSS}
C {sym/gnd.sym} 404 540 0 0 {name=l12 lab=VSS}
C {sym/gnd.sym} 634 540 0 0 {name=l13 lab=VSS}
C {sym/ipin.sym} 312 540 0 2 {name=l14 lab=vinp}
C {sym/ipin.sym} 542 540 0 2 {name=l15 lab=vinn}
C {sym/opin.sym} 380 290 0 0 {name=l16 lab=s1n}
C {sym/opin.sym} 610 290 0 0 {name=l17 lab=s1p}
C {sym/lab_pin.sym} 962 210 0 2 {name=l18 lab=outp}
C {sym/lab_pin.sym} 962 380 0 2 {name=l19 lab=outp}
C {sym/lab_pin.sym} 1192 210 0 2 {name=l20 lab=outn}
C {sym/lab_pin.sym} 1192 380 0 2 {name=l21 lab=outn}
C {sym/lab_pin.sym} 802 210 0 2 {name=l22 lab=clk}
C {sym/lab_pin.sym} 802 380 0 2 {name=l23 lab=clk}
C {sym/lab_pin.sym} 1352 210 0 2 {name=l24 lab=clk}
C {sym/lab_pin.sym} 1352 380 0 2 {name=l25 lab=clk}
C {sym/lab_pin.sym} 1077 670 0 2 {name=l26 lab=clk}
C {sym/gnd.sym} 1054 380 0 0 {name=l27 lab=VSS}
C {sym/gnd.sym} 1284 380 0 0 {name=l28 lab=VSS}
C {sym/gnd.sym} 1054 540 0 0 {name=l29 lab=VSS}
C {sym/gnd.sym} 1284 540 0 0 {name=l30 lab=VSS}
C {sym/lab_pin.sym} 962 540 0 2 {name=l31 lab=s1p}
C {sym/lab_pin.sym} 1192 540 0 2 {name=l32 lab=s1n}
C {sym/opin.sym} 1030 290 0 0 {name=l33 lab=outn}
C {sym/opin.sym} 1260 290 0 0 {name=l34 lab=outp}
C {sym/vdd.sym} 160 82 0 1 {name=l35 lab=VDD}
C {sym/gnd.sym} 495 788 0 3 {name=l36 lab=VSS}
T {offset Vo1-4 injected on stage-1 input/latch gates (testbench)} 160 824 0 0 0.26 0.26 {layer=7}
N 160 110 1440 110 {}
N 160 760 1440 760 {}
N 380 180 380 110 {}
N 610 180 610 110 {}
N 220 180 220 110 {}
N 770 180 770 110 {}
N 220 350 220 110 {}
N 770 350 770 110 {}
N 380 240 380 350 {}
N 610 240 610 350 {}
N 380 410 380 510 {}
N 610 410 610 510 {}
N 220 240 220 290 {}
N 220 290 380 290 {}
N 770 240 770 290 {}
N 770 290 610 290 {}
N 220 410 220 460 {}
N 220 460 380 460 {}
N 770 410 770 460 {}
N 770 460 610 460 {}
N 380 570 380 610 {}
N 610 570 610 610 {}
N 380 610 610 610 {}
N 495 610 495 640 {}
N 495 700 495 760 {}
N 380 210 380 180 {}
N 610 210 610 180 {}
N 220 210 220 180 {}
N 770 210 770 180 {}
N 220 380 220 350 {}
N 770 380 770 350 {}
N 495 670 495 700 {}
N 1030 180 1030 110 {}
N 1260 180 1260 110 {}
N 870 180 870 110 {}
N 1420 180 1420 110 {}
N 870 350 870 110 {}
N 1420 350 1420 110 {}
N 1030 240 1030 350 {}
N 1260 240 1260 350 {}
N 1030 410 1030 510 {}
N 1260 410 1260 510 {}
N 870 240 870 290 {}
N 870 290 1030 290 {}
N 1420 240 1420 290 {}
N 1420 290 1260 290 {}
N 870 410 870 460 {}
N 870 460 1030 460 {}
N 1420 410 1420 460 {}
N 1420 460 1260 460 {}
N 1030 570 1030 610 {}
N 1260 570 1260 610 {}
N 1030 610 1260 610 {}
N 1145 610 1145 640 {}
N 1145 700 1145 760 {}
N 1030 210 1030 180 {}
N 1260 210 1260 180 {}
N 870 210 870 180 {}
N 1420 210 1420 180 {}
N 870 380 870 350 {}
N 1420 380 1420 350 {}
N 1145 670 1145 700 {}
N 340 210 312 210 {}
N 340 380 312 380 {}
N 570 210 542 210 {}
N 570 380 542 380 {}
N 180 210 152 210 {}
N 180 380 152 380 {}
N 730 210 702 210 {}
N 730 380 702 380 {}
N 455 670 427 670 {}
N 380 380 404 380 {}
N 610 380 634 380 {}
N 380 540 404 540 {}
N 610 540 634 540 {}
N 340 540 312 540 {}
N 570 540 542 540 {}
N 990 210 962 210 {}
N 990 380 962 380 {}
N 1220 210 1192 210 {}
N 1220 380 1192 380 {}
N 830 210 802 210 {}
N 830 380 802 380 {}
N 1380 210 1352 210 {}
N 1380 380 1352 380 {}
N 1105 670 1077 670 {}
N 1030 380 1054 380 {}
N 1260 380 1284 380 {}
N 1030 540 1054 540 {}
N 1260 540 1284 540 {}
N 990 540 962 540 {}
N 1220 540 1192 540 {}
N 160 110 160 82 {}
N 495 760 495 788 {}
