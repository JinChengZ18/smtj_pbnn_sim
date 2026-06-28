v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/pfet.sym} 300 210 0 0 {name=M5 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 520 210 0 0 {name=M6 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 150 210 0 0 {name=Mp2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 670 210 0 0 {name=Mp1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 300 380 0 0 {name=M3 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 520 380 0 0 {name=M4 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 90 380 0 0 {name=Mp3 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 730 380 0 0 {name=Mp4 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 300 540 0 0 {name=M1 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 520 540 0 0 {name=M2 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 410 690 0 0 {name=Mtail model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
N 70 110 750 110 {}
N 320 790 540 790 {}
N 320 180 320 110 {}
N 540 180 540 110 {}
N 170 180 170 110 {}
N 690 180 690 110 {}
N 110 350 110 110 {}
N 750 350 750 110 {}
N 320 240 320 350 {}
N 540 240 540 350 {}
N 320 410 320 510 {}
N 540 410 540 510 {}
N 170 240 170 270 {}
N 170 270 320 270 {}
N 690 240 690 270 {}
N 690 270 540 270 {}
N 110 410 110 440 {}
N 110 440 320 440 {}
N 750 410 750 440 {}
N 750 440 540 440 {}
N 320 570 320 630 {}
N 540 570 540 630 {}
N 320 630 540 630 {}
N 430 630 430 660 {}
N 430 720 430 790 {}
N 320 210 320 180 {}
N 540 210 540 180 {}
N 170 210 170 180 {}
N 690 210 690 180 {}
N 110 380 110 350 {}
N 750 380 750 350 {}
N 430 690 430 720 {}
N 280 210 250 210 {}
C {sym/lab_pin.sym} 250 210 0 2 {name=l1 lab=outp}
N 280 380 250 380 {}
C {sym/lab_pin.sym} 250 380 0 2 {name=l2 lab=outp}
N 500 210 470 210 {}
C {sym/lab_pin.sym} 470 210 0 2 {name=l3 lab=outn}
N 500 380 470 380 {}
C {sym/lab_pin.sym} 470 380 0 2 {name=l4 lab=outn}
N 130 210 100 210 {}
C {sym/lab_pin.sym} 100 210 0 2 {name=l5 lab=clk}
N 650 210 620 210 {}
C {sym/lab_pin.sym} 620 210 0 2 {name=l6 lab=clk}
N 70 380 40 380 {}
C {sym/lab_pin.sym} 40 380 0 2 {name=l7 lab=clk}
N 710 380 680 380 {}
C {sym/lab_pin.sym} 680 380 0 2 {name=l8 lab=clk}
N 390 690 360 690 {}
C {sym/lab_pin.sym} 360 690 0 2 {name=l9 lab=clk}
N 320 380 345 380 {}
C {sym/gnd.sym} 345 380 0 0 {name=l10 lab=VSS}
N 540 380 565 380 {}
C {sym/gnd.sym} 565 380 0 0 {name=l11 lab=VSS}
N 320 540 345 540 {}
C {sym/gnd.sym} 345 540 0 0 {name=l12 lab=VSS}
N 540 540 565 540 {}
C {sym/gnd.sym} 565 540 0 0 {name=l13 lab=VSS}
N 280 540 250 540 {}
C {sym/ipin.sym} 250 540 0 2 {name=l14 lab=vinp}
N 500 540 470 540 {}
C {sym/ipin.sym} 470 540 0 2 {name=l15 lab=vinn}
C {sym/opin.sym} 320 270 0 0 {name=l16 lab=outn}
C {sym/opin.sym} 540 270 0 0 {name=l17 lab=outp}
N 70 110 70 82 {}
C {sym/vdd.sym} 70 82 0 1 {name=l18 lab=VDD}
N 320 790 320 818 {}
C {sym/gnd.sym} 320 818 0 3 {name=l19 lab=VSS}
