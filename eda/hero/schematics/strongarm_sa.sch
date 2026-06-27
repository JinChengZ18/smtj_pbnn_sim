v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sky130_fd_pr/pfet_01v8.sym} 440 240 0 0 {name=M5 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/pfet_01v8.sym} 740 240 0 0 {name=M6 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/pfet_01v8.sym} 240 240 0 0 {name=Mp2 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/pfet_01v8.sym} 940 240 0 0 {name=Mp1 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/nfet_01v8.sym} 440 480 0 0 {name=M3 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/nfet_01v8.sym} 740 480 0 0 {name=M4 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/pfet_01v8.sym} 120 480 0 0 {name=Mp3 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/pfet_01v8.sym} 1060 480 0 0 {name=Mp4 model=sky130_fd_pr__pfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sky130_fd_pr/nfet_01v8.sym} 440 700 0 0 {name=M1 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sky130_fd_pr/nfet_01v8.sym} 740 700 0 0 {name=M2 model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sky130_fd_pr/nfet_01v8.sym} 590 900 0 0 {name=Mtail model=sky130_fd_pr__nfet_01v8 W=4 L=0.15 nf=1 m=1}
N 120 120 1080 120 {}
N 400 1000 780 1000 {}
N 460 210 460 120 {}
N 760 210 760 120 {}
N 260 210 260 120 {}
N 960 210 960 120 {}
N 140 450 140 120 {}
N 1080 450 1080 120 {}
N 460 270 460 450 {}
N 760 270 760 450 {}
N 460 510 460 670 {}
N 760 510 760 670 {}
N 260 270 260 330 {}
N 260 330 460 330 {}
N 960 270 960 330 {}
N 960 330 760 330 {}
N 140 510 140 560 {}
N 140 560 460 560 {}
N 1080 510 1080 560 {}
N 1080 560 760 560 {}
N 460 730 460 800 {}
N 760 730 760 800 {}
N 460 800 760 800 {}
N 610 800 610 870 {}
N 610 930 610 1000 {}
N 420 240 420 480 {}
N 720 240 720 480 {}
N 760 400 420 400 {}
N 460 300 720 300 {}
N 460 240 460 210 {}
N 760 240 760 210 {}
N 260 240 260 210 {}
N 960 240 960 210 {}
N 140 480 140 450 {}
N 1080 480 1080 450 {}
N 610 900 610 930 {}
N 220 240 190 240 {}
C {devices/lab_pin.sym} 190 240 0 2 {name=k1 lab=clk}
N 920 240 890 240 {}
C {devices/lab_pin.sym} 890 240 0 2 {name=k2 lab=clk}
N 100 480 70 480 {}
C {devices/lab_pin.sym} 70 480 0 2 {name=k3 lab=clk}
N 1040 480 1010 480 {}
C {devices/lab_pin.sym} 1010 480 0 2 {name=k4 lab=clk}
N 570 900 540 900 {}
C {devices/lab_pin.sym} 540 900 0 2 {name=k5 lab=clk}
N 460 480 485 480 {}
C {devices/lab_pin.sym} 485 480 0 0 {name=b6 lab=VSS}
N 760 480 785 480 {}
C {devices/lab_pin.sym} 785 480 0 0 {name=b7 lab=VSS}
N 460 700 485 700 {}
C {devices/lab_pin.sym} 485 700 0 0 {name=b8 lab=VSS}
N 760 700 785 700 {}
C {devices/lab_pin.sym} 785 700 0 0 {name=b9 lab=VSS}
C {devices/ipin.sym} 390 700 0 2 {name=ivp lab=vinp}
N 420 700 390 700 {}
C {devices/ipin.sym} 690 700 0 2 {name=ivn lab=vinn}
N 720 700 690 700 {}
C {devices/opin.sym} 460 300 0 0 {name=oon lab=outn}
C {devices/opin.sym} 760 400 0 0 {name=oop lab=outp}
N 120 120 120 90 {}
C {devices/lab_pin.sym} 120 90 0 1 {name=vddl lab=VDD}
N 400 1000 400 1030 {}
C {devices/lab_pin.sym} 400 1030 0 3 {name=vssl lab=VSS}
