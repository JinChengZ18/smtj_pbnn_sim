v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/pfet.sym} 200 300 0 0 {name=Mref model=sky130_fd_pr__pfet_01v8 W=1 L=0.5 nf=1 m=1}
C {sym/pfet.sym} 400 300 0 0 {name=Mb0 model=sky130_fd_pr__pfet_01v8 W=1 L=0.5 nf=1 m=1}
C {sym/pfet.sym} 540 300 0 0 {name=Mb1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.5 nf=1 m=1}
C {sym/pfet.sym} 680 300 0 0 {name=Mb2 model=sky130_fd_pr__pfet_01v8 W=4 L=0.5 nf=1 m=1}
C {sym/pfet.sym} 820 300 0 0 {name=Mb3 model=sky130_fd_pr__pfet_01v8 W=8 L=0.5 nf=1 m=1}
C {sym/pfet.sym} 960 300 0 0 {name=Mb4 model=sky130_fd_pr__pfet_01v8 W=16 L=0.5 nf=1 m=1}
C {sym/pfet.sym} 1100 300 0 0 {name=Mb5 model=sky130_fd_pr__pfet_01v8 W=32 L=0.5 nf=1 m=1}
C {sym/res.sym} 200 520 0 0 {name=Rref value=147k}
C {sym/res.sym} 1230 520 0 0 {name=Rload value=776}
N 220 200 1120 200 {}
N 220 270 220 200 {}
N 220 300 220 270 {}
N 420 270 420 200 {}
N 420 300 420 270 {}
N 560 270 560 200 {}
N 560 300 560 270 {}
N 700 270 700 200 {}
N 700 300 700 270 {}
N 840 270 840 200 {}
N 840 300 840 270 {}
N 980 270 980 200 {}
N 980 300 980 270 {}
N 1120 270 1120 200 {}
N 1120 300 1120 270 {}
N 220 330 220 360 {}
N 120 360 220 360 {}
N 120 300 120 360 {}
N 120 300 180 300 {}
N 120 300 1080 300 {}
N 120 360 200 360 {}
N 200 360 200 490 {}
N 200 550 200 610 {}
N 420 330 420 430 {}
N 560 330 560 430 {}
N 700 330 700 430 {}
N 840 330 840 430 {}
N 980 330 980 430 {}
N 1120 330 1120 430 {}
N 420 430 1230 430 {}
N 1230 430 1230 490 {}
N 1230 550 1230 610 {}
N 220 200 220 172 {}
C {sym/vdd.sym} 220 172 0 1 {name=l1 lab=VDD}
N 200 610 200 610 {}
C {sym/gnd.sym} 200 610 0 0 {name=l2 lab=VSS}
N 1230 610 1230 610 {}
C {sym/gnd.sym} 1230 610 0 0 {name=l3 lab=VSS}
C {sym/opin.sym} 1230 430 0 0 {name=l4 lab=load}
T {vbias} 124 292 0 0 0.22 0.22 {}
T {b0 (W=1)} 372 242 0 0 0.2 0.2 {}
T {b1 (W=2)} 512 242 0 0 0.2 0.2 {}
T {b2 (W=4)} 652 242 0 0 0.2 0.2 {}
T {b3 (W=8)} 792 242 0 0 0.2 0.2 {}
T {b4 (W=16)} 932 242 0 0 0.2 0.2 {}
T {b5 (W=32)} 1072 242 0 0 0.2 0.2 {}
T {Iu} 176 242 0 0 0.2 0.2 {}
