v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/sot_mtj.sym} 200 190 0 0 {name=Nsm}
C {sym/nfet.sym} 180 440 0 0 {name=DN model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 430 210 0 0 {name=VPE1 model=sky130_fd_pr__pfet_01v8 W=0.84 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 430 320 0 0 {name=VPI1 model=sky130_fd_pr__pfet_01v8 W=0.42 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 430 440 0 0 {name=VNI1 model=sky130_fd_pr__nfet_01v8 W=0.42 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 430 550 0 0 {name=VNE1 model=sky130_fd_pr__nfet_01v8 W=0.84 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 600 210 0 0 {name=VPE2 model=sky130_fd_pr__pfet_01v8 W=26 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 600 320 0 0 {name=VPI2 model=sky130_fd_pr__pfet_01v8 W=13 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 600 440 0 0 {name=VNI2 model=sky130_fd_pr__nfet_01v8 W=2.1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 600 550 0 0 {name=VNE2 model=sky130_fd_pr__nfet_01v8 W=4.2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 800 320 0 0 {name=BP model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 800 440 0 0 {name=BN model=sky130_fd_pr__nfet_01v8 W=0.84 L=0.15 nf=1 m=1}
N 140 110 820 110 {}
N 200 630 820 630 {}
N 200 150 200 110 {}
N 240 210 240 260 {}
N 240 260 200 260 {}
N 200 260 200 410 {}
N 200 470 200 630 {}
N 450 180 450 110 {}
N 450 210 450 180 {}
N 450 240 450 290 {}
N 450 350 450 380 {}
N 450 380 450 410 {}
N 450 470 450 520 {}
N 450 580 450 630 {}
N 620 180 620 110 {}
N 620 210 620 180 {}
N 620 240 620 290 {}
N 620 350 620 380 {}
N 620 380 620 410 {}
N 620 470 620 520 {}
N 620 580 620 630 {}
N 450 380 620 380 {}
N 620 380 760 380 {}
N 820 290 820 110 {}
N 820 320 820 290 {}
N 820 350 820 380 {}
N 820 380 820 410 {}
N 820 470 820 630 {}
N 780 320 760 320 {}
N 760 320 760 380 {}
N 760 380 760 440 {}
N 760 440 780 440 {}
N 410 210 380 210 {}
C {sym/lab_pin.sym} 380 210 0 2 {name=l1 lab=enp1}
N 580 210 550 210 {}
C {sym/lab_pin.sym} 550 210 0 2 {name=l2 lab=enp2}
N 410 550 380 550 {}
C {sym/lab_pin.sym} 380 550 0 2 {name=l3 lab=enn1}
N 580 550 550 550 {}
C {sym/lab_pin.sym} 550 550 0 2 {name=l4 lab=enn2}
N 410 320 380 320 {}
C {sym/lab_pin.sym} 380 320 0 2 {name=l5 lab=vdiv}
N 580 320 550 320 {}
C {sym/lab_pin.sym} 550 320 0 2 {name=l6 lab=vdiv}
N 410 440 380 440 {}
C {sym/lab_pin.sym} 380 440 0 2 {name=l7 lab=vdiv}
N 580 440 550 440 {}
C {sym/lab_pin.sym} 550 440 0 2 {name=l8 lab=vdiv}
N 160 440 130 440 {}
C {sym/ipin.sym} 130 440 0 2 {name=l9 lab=vb}
N 160 210 130 210 {}
C {sym/lab_pin.sym} 130 210 0 2 {name=l10 lab=vdiv}
C {sym/lab_pin.sym} 200 330 0 0 {name=l11 lab=vdiv}
C {sym/lab_pin.sym} 515 380 0 0 {name=l12 lab=vtcout}
C {sym/lab_pin.sym} 450 265 0 0 {name=l13 lab=Vp1}
C {sym/lab_pin.sym} 450 495 0 0 {name=l14 lab=Vn1}
C {sym/lab_pin.sym} 620 265 0 0 {name=l15 lab=Vp2}
C {sym/lab_pin.sym} 620 495 0 0 {name=l16 lab=Vn2}
N 820 380 860 380 {}
C {sym/opin.sym} 860 380 0 0 {name=l17 lab=final}
N 200 440 225 440 {}
C {sym/gnd.sym} 225 440 0 0 {name=l18 lab=VSS}
N 450 440 475 440 {}
C {sym/gnd.sym} 475 440 0 0 {name=l19 lab=VSS}
N 450 550 475 550 {}
C {sym/gnd.sym} 475 550 0 0 {name=l20 lab=VSS}
N 620 440 645 440 {}
C {sym/gnd.sym} 645 440 0 0 {name=l21 lab=VSS}
N 620 550 645 550 {}
C {sym/gnd.sym} 645 550 0 0 {name=l22 lab=VSS}
N 820 440 845 440 {}
C {sym/gnd.sym} 845 440 0 0 {name=l23 lab=VSS}
N 450 320 475 320 {}
C {sym/vdd.sym} 475 320 0 0 {name=l24 lab=VDD}
N 620 320 645 320 {}
C {sym/vdd.sym} 645 320 0 0 {name=l25 lab=VDD}
N 140 110 140 82 {}
C {sym/vdd.sym} 140 82 0 1 {name=l26 lab=VDD}
N 280 630 280 658 {}
C {sym/gnd.sym} 280 658 0 3 {name=l27 lab=VSS}
T {R_P = 4.9k} 52 158 0 0 0.2 0.2 {}
T {R_AP = 9.8k} 52 178 0 0 0.2 0.2 {}
T {SOT track tied:} 28 272 0 0 0.18 0.18 {}
T {V_wr = 0} 28 292 0 0 0.18 0.18 {}
