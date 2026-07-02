v {xschem version=3.4.4 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
C {sym/res.sym} 160 75 0 0 {name=RlT value=6.75k m=1}
C {sym/res.sym} 160 190 0 0 {name=Rl7 value=750 m=1}
C {sym/res.sym} 160 300 0 0 {name=Rl6 value=750 m=1}
C {sym/res.sym} 160 410 0 0 {name=Rl5 value=750 m=1}
C {sym/res.sym} 160 520 0 0 {name=Rl4 value=750 m=1}
C {sym/res.sym} 160 630 0 0 {name=Rl3 value=750 m=1}
C {sym/res.sym} 160 740 0 0 {name=Rl2 value=750 m=1}
C {sym/res.sym} 160 850 0 0 {name=RlB value=6.75k m=1}
C {sym/cap.sym} 100 825 0 0 {name=Cdec1 value=0.5p m=1}
C {sym/cap.sym} 100 715 0 0 {name=Cdec2 value=0.5p m=1}
C {sym/cap.sym} 100 605 0 0 {name=Cdec3 value=0.5p m=1}
C {sym/cap.sym} 100 495 0 0 {name=Cdec4 value=0.5p m=1}
C {sym/cap.sym} 100 385 0 0 {name=Cdec5 value=0.5p m=1}
C {sym/cap.sym} 100 275 0 0 {name=Cdec6 value=0.5p m=1}
C {sym/cap.sym} 100 165 0 0 {name=Cdec7 value=0.5p m=1}
C {sym/comp.sym} 620 780 0 0 {name=SA1}
C {sym/comp.sym} 620 670 0 0 {name=SA2}
C {sym/comp.sym} 620 560 0 0 {name=SA3}
C {sym/comp.sym} 620 450 0 0 {name=SA4}
C {sym/comp.sym} 620 340 0 0 {name=SA5}
C {sym/comp.sym} 620 230 0 0 {name=SA6}
C {sym/comp.sym} 620 120 0 0 {name=SA7}
C {sym/res.sym} 350 1020 0 0 {name=Rti0 value=1225 m=1}
C {sym/pfet.sym} 280 1110 0 0 {name=TGp0 model=sky130_fd_pr__pfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 420 1110 0 0 {name=TGn0 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/res.sym} 710 1020 0 0 {name=Rti7 value=1225 m=1}
C {sym/pfet.sym} 640 1110 0 0 {name=TGp7 model=sky130_fd_pr__pfet_01v8 W=4 L=0.15 nf=1 m=1}
C {sym/nfet.sym} 780 1110 0 0 {name=TGn7 model=sky130_fd_pr__nfet_01v8 W=2 L=0.15 nf=1 m=1}
C {sym/cap.sym} 450 1230 0 0 {name=Cadc value=3.5p m=1}
N 160 105 160 135 {}
N 160 135 160 160 {}
N 160 220 160 245 {}
N 160 245 160 270 {}
N 160 330 160 355 {}
N 160 355 160 380 {}
N 160 440 160 465 {}
N 160 465 160 490 {}
N 160 550 160 575 {}
N 160 575 160 600 {}
N 160 660 160 685 {}
N 160 685 160 710 {}
N 160 770 160 795 {}
N 160 795 160 820 {}
N 100 795 160 795 {}
N 160 795 580 795 {}
N 100 685 160 685 {}
N 160 685 580 685 {}
N 100 575 160 575 {}
N 160 575 580 575 {}
N 100 465 160 465 {}
N 160 465 580 465 {}
N 100 355 160 355 {}
N 160 355 580 355 {}
N 100 245 160 245 {}
N 160 245 580 245 {}
N 100 135 160 135 {}
N 160 135 580 135 {}
N 520 105 520 1200 {}
N 520 765 580 765 {}
N 665 780 700 780 {}
N 520 655 580 655 {}
N 665 670 700 670 {}
N 520 545 580 545 {}
N 665 560 700 560 {}
N 520 435 580 435 {}
N 665 450 700 450 {}
N 520 325 580 325 {}
N 665 340 700 340 {}
N 520 215 580 215 {}
N 665 230 700 230 {}
N 520 105 580 105 {}
N 665 120 700 120 {}
N 350 970 350 990 {}
N 350 1050 350 1080 {}
N 300 1080 440 1080 {}
N 300 1140 440 1140 {}
N 370 1140 370 1200 {}
N 710 970 710 990 {}
N 710 1050 710 1080 {}
N 660 1080 800 1080 {}
N 660 1140 800 1140 {}
N 730 1140 730 1200 {}
N 370 1200 730 1200 {}
N 160 45 160 17 {}
C {sym/vdd.sym} 160 17 0 1 {name=l1 lab=vddl}
N 160 880 160 905 {}
C {sym/gnd.sym} 160 905 0 3 {name=l2 lab=GND}
C {sym/lab_pin.sym} 240 795 0 0 {name=l3 lab=tap1}
N 100 855 100 870 {}
C {sym/gnd.sym} 100 870 0 3 {name=l4 lab=GND}
C {sym/lab_pin.sym} 240 685 0 0 {name=l5 lab=tap2}
N 100 745 100 760 {}
C {sym/gnd.sym} 100 760 0 3 {name=l6 lab=GND}
C {sym/lab_pin.sym} 240 575 0 0 {name=l7 lab=tap3}
N 100 635 100 650 {}
C {sym/gnd.sym} 100 650 0 3 {name=l8 lab=GND}
C {sym/lab_pin.sym} 240 465 0 0 {name=l9 lab=tap4}
N 100 525 100 540 {}
C {sym/gnd.sym} 100 540 0 3 {name=l10 lab=GND}
C {sym/lab_pin.sym} 240 355 0 0 {name=l11 lab=tap5}
N 100 415 100 430 {}
C {sym/gnd.sym} 100 430 0 3 {name=l12 lab=GND}
C {sym/lab_pin.sym} 240 245 0 0 {name=l13 lab=tap6}
N 100 305 100 320 {}
C {sym/gnd.sym} 100 320 0 3 {name=l14 lab=GND}
C {sym/lab_pin.sym} 240 135 0 0 {name=l15 lab=tap7}
N 100 195 100 210 {}
C {sym/gnd.sym} 100 210 0 3 {name=l16 lab=GND}
C {sym/opin.sym} 700 780 0 0 {name=l17 lab=t1}
C {sym/opin.sym} 700 670 0 0 {name=l18 lab=t2}
C {sym/opin.sym} 700 560 0 0 {name=l19 lab=t3}
C {sym/opin.sym} 700 450 0 0 {name=l20 lab=t4}
C {sym/opin.sym} 700 340 0 0 {name=l21 lab=t5}
C {sym/opin.sym} 700 230 0 0 {name=l22 lab=t6}
C {sym/opin.sym} 700 120 0 0 {name=l23 lab=t7}
C {sym/lab_pin.sym} 520 870 0 0 {name=l24 lab=vin}
C {sym/ipin.sym} 350 970 0 1 {name=l25 lab=col0}
N 260 1110 230 1110 {}
C {sym/lab_pin.sym} 230 1110 0 2 {name=l26 lab=sel0b}
N 400 1110 370 1110 {}
C {sym/lab_pin.sym} 370 1110 0 2 {name=l27 lab=sel0}
N 300 1110 325 1110 {}
C {sym/vdd.sym} 325 1110 0 0 {name=l28 lab=VDD}
N 440 1110 465 1110 {}
C {sym/gnd.sym} 465 1110 0 0 {name=l29 lab=GND}
C {sym/ipin.sym} 710 970 0 1 {name=l30 lab=col7}
N 620 1110 590 1110 {}
C {sym/lab_pin.sym} 590 1110 0 2 {name=l31 lab=sel7b}
N 760 1110 730 1110 {}
C {sym/lab_pin.sym} 730 1110 0 2 {name=l32 lab=sel7}
N 660 1110 685 1110 {}
C {sym/vdd.sym} 685 1110 0 0 {name=l33 lab=VDD}
N 800 1110 825 1110 {}
C {sym/gnd.sym} 825 1110 0 0 {name=l34 lab=GND}
N 450 1260 450 1275 {}
C {sym/gnd.sym} 450 1275 0 3 {name=l35 lab=GND}
T {. . .} 440 1020 0 0 0.4 0.4 {}
T {strobed in parallel (clk)} 610 50 0 0 0.24 0.24 {}
