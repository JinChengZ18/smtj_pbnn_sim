v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/pfet.sym} 560 200 0 0 {name=Na3 model=sky130_fd_pr__pfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 700 200 0 0 {name=Na4 model=sky130_fd_pr__pfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 560 330 0 0 {name=Na1 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 560 420 0 0 {name=Na2 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 840 200 0 0 {name=Ia2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 840 330 0 0 {name=Ia1 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1080 200 0 0 {name=Nb3 model=sky130_fd_pr__pfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1220 200 0 0 {name=Nb4 model=sky130_fd_pr__pfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1080 330 0 0 {name=Nb1 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1080 420 0 0 {name=Nb2 model=sky130_fd_pr__nfet_01v8 W=1 L=0.15 nf=1 m=1}
C {sym/pfet.sym} 1360 200 0 0 {name=Ib2 model=sky130_fd_pr__pfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 1360 330 0 0 {name=Ib1 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/comp.sym} 320 180 0 0 {name=CMP2A}
C {sym/comp.sym} 320 340 0 0 {name=CMP2B}
C {sym/comp.sym} 320 620 0 0 {name=CMP1}
N 120 120 120 605 {}
N 120 165 280 165 {}
N 120 325 280 325 {}
N 120 605 280 605 {}
N 170 90 170 635 {}
N 170 195 280 195 {}
N 170 355 280 355 {}
N 170 635 280 635 {}
N 295 210 295 235 {}
N 295 235 240 235 {}
N 295 370 295 395 {}
N 295 395 240 395 {}
N 365 180 410 180 {}
N 365 340 410 340 {}
N 365 620 410 620 {}
N 580 230 720 230 {}
N 580 230 580 300 {}
N 580 360 580 390 {}
N 1100 230 1240 230 {}
N 1100 230 1100 300 {}
N 1100 360 1100 390 {}
N 820 200 790 200 {}
N 820 330 790 330 {}
N 790 200 790 330 {}
N 860 230 860 300 {}
N 1340 200 1310 200 {}
N 1340 330 1310 330 {}
N 1310 200 1310 330 {}
N 1380 230 1380 300 {}
N 580 265 790 265 {}
N 1100 265 1310 265 {}
N 1380 265 1470 265 {}
N 1470 265 1470 720 {}
N 1470 720 295 720 {}
N 295 720 295 650 {}
N 580 200 580 170 {}
N 720 200 720 170 {}
N 860 200 860 170 {}
N 1100 200 1100 170 {}
N 1240 200 1240 170 {}
N 1380 200 1380 170 {}
N 540 200 510 200 {}
C {sym/lab_pin.sym} 510 200 0 2 {name=l1 lab=outna}
N 540 330 510 330 {}
C {sym/lab_pin.sym} 510 330 0 2 {name=l2 lab=outna}
N 680 200 650 200 {}
C {sym/lab_pin.sym} 650 200 0 2 {name=l3 lab=outpb}
N 540 420 510 420 {}
C {sym/lab_pin.sym} 510 420 0 2 {name=l4 lab=outpb}
N 1060 200 1030 200 {}
C {sym/lab_pin.sym} 1030 200 0 2 {name=l5 lab=clk_raw}
N 1060 330 1030 330 {}
C {sym/lab_pin.sym} 1030 330 0 2 {name=l6 lab=clk_raw}
N 1200 200 1170 200 {}
C {sym/lab_pin.sym} 1170 200 0 2 {name=l7 lab=amb}
N 1060 420 1030 420 {}
C {sym/lab_pin.sym} 1030 420 0 2 {name=l8 lab=amb}
N 580 170 580 145 {}
C {sym/vdd.sym} 580 145 0 1 {name=l9 lab=VDD}
N 720 170 720 145 {}
C {sym/vdd.sym} 720 145 0 1 {name=l10 lab=VDD}
N 860 170 860 145 {}
C {sym/vdd.sym} 860 145 0 1 {name=l11 lab=VDD}
N 1100 170 1100 145 {}
C {sym/vdd.sym} 1100 145 0 1 {name=l12 lab=VDD}
N 1240 170 1240 145 {}
C {sym/vdd.sym} 1240 145 0 1 {name=l13 lab=VDD}
N 1380 170 1380 145 {}
C {sym/vdd.sym} 1380 145 0 1 {name=l14 lab=VDD}
N 580 450 580 475 {}
C {sym/gnd.sym} 580 475 0 3 {name=l15 lab=VSS}
N 860 360 860 385 {}
C {sym/gnd.sym} 860 385 0 3 {name=l16 lab=VSS}
N 1100 450 1100 475 {}
C {sym/gnd.sym} 1100 475 0 3 {name=l17 lab=VSS}
N 1380 360 1380 385 {}
C {sym/gnd.sym} 1380 385 0 3 {name=l18 lab=VSS}
N 580 330 605 330 {}
C {sym/gnd.sym} 605 330 0 0 {name=l19 lab=VSS}
N 580 420 605 420 {}
C {sym/gnd.sym} 605 420 0 0 {name=l20 lab=VSS}
N 860 330 885 330 {}
C {sym/gnd.sym} 885 330 0 0 {name=l21 lab=VSS}
N 1100 330 1125 330 {}
C {sym/gnd.sym} 1125 330 0 0 {name=l22 lab=VSS}
N 1100 420 1125 420 {}
C {sym/gnd.sym} 1125 420 0 0 {name=l23 lab=VSS}
N 1380 330 1405 330 {}
C {sym/gnd.sym} 1405 330 0 0 {name=l24 lab=VSS}
C {sym/ipin.sym} 120 120 0 1 {name=l25 lab=vinp}
C {sym/ipin.sym} 170 90 0 1 {name=l26 lab=vinn}
C {sym/lab_pin.sym} 240 235 0 2 {name=l27 lab=clk2}
C {sym/lab_pin.sym} 240 395 0 2 {name=l28 lab=clk2}
C {sym/lab_pin.sym} 410 180 0 0 {name=l29 lab=outna}
C {sym/lab_pin.sym} 410 340 0 0 {name=l30 lab=outpb}
C {sym/opin.sym} 410 620 0 0 {name=l31 lab=outp1}
C {sym/lab_pin.sym} 700 265 0 0 {name=l32 lab=n1}
C {sym/lab_pin.sym} 1210 265 0 0 {name=l33 lab=n2}
C {sym/lab_pin.sym} 860 265 0 0 {name=l34 lab=amb}
C {sym/lab_pin.sym} 600 720 0 0 {name=l35 lab=cclk1}
T {ref +Vg} 302 216 0 0 0.22 0.22 {}
T {W=0.42 (near-min)} 302 238 0 0 0.2 0.2 {}
T {ref -Vg} 302 376 0 0 0.22 0.22 {}
T {W=0.42 (near-min)} 302 398 0 0 0.2 0.2 {}
T {committed StrongARM} 302 656 0 0 0.2 0.2 {}
T {W=2-4, L=0.15} 302 678 0 0 0.2 0.2 {}
T {NAND2} 548 502 0 0 0.22 0.22 {}
T {NAND2} 1068 502 0 0 0.22 0.22 {}
T {INV} 846 412 0 0 0.22 0.22 {}
T {INV (drv)} 1346 412 0 0 0.22 0.22 {}
T {amb = AND(outna, outpb)} 560 540 0 0 0.24 0.24 {}
T {cclk1 = AND(clk_raw, amb)} 1080 540 0 0 0.24 0.24 {}
