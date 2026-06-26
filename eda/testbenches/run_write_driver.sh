#!/bin/bash
# Plan 3.1 (errata R4): end-to-end write energy with a REAL sky130 CMOS driver into the
# 776 ohm SOT write load. Sweeps the pull-up width W_p; for each, ngspice transient ->
# supply energy E_vdd, device energy E_dev, driver overhead, delivered flat-top V, peak I.
# The device write branch == its R_SOT=776 ohm (the .va confirms 776), so no OSDI needed here:
# this isolates the DRIVER overhead (Ron IR-loss + short-circuit + switching) that the
# 0.783 pJ Ohmic-only number omits.
#
# INVOKE: wsl -d Ubuntu-24.04-EDA -- bash -lc \
#   'cd "<repo>/eda/testbenches" && bash run_write_driver.sh'
set -u
NG=$(command -v ngspice || echo /usr/bin/ngspice)
LIB=/opt/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice
BUILD=/home/lenovo/smtj_eda_build
mkdir -p "$BUILD"
echo "ngspice=$NG"
echo "  W_p(um)  vflat(V)  Idev_pk(mA)  E_dev(pJ)  E_vdd(pJ)  overhead%   (VDD=1.8, R_SOT=776, tw=0.75ns)"
for WP in 1 2 4 6 7 8 16 32 64; do
  cat > "$BUILD/wdrv.spice" <<EOF
* 3.1 sky130 CMOS write driver -> 776 ohm SOT load (R4)
.lib $LIB tt
.param VDD=1.8 wp=$WP wn=8 L=0.15 tw=0.75n tr=0.05n RSOT=776
Vdd vdd 0 {VDD}
Vgin gin 0 PULSE({VDD} 0 0.2n {tr} {tr} {tw} 10n)
XMP vdd gin wr vdd sky130_fd_pr__pfet_01v8 W={wp} L={L}
XMN wr  gin 0  0   sky130_fd_pr__nfet_01v8 W={wn} L={L}
Rsot wr com {RSOT}
Vcom com 0 dc 0
.control
  tran 0.2p 4n
  let p_vdd = -v(vdd)*i(vdd)
  let p_dev = v(wr)*i(Vcom)
  meas tran e_vdd integ p_vdd from=0 to=4n
  meas tran e_dev integ p_dev from=0 to=4n
  meas tran vflat MAX v(wr)
  meas tran idev MAX i(Vcom)
  quit
.endc
.end
EOF
  out=$("$NG" -b "$BUILD/wdrv.spice" 2>/dev/null)
  evdd=$(echo "$out" | awk '/e_vdd/{print $3; exit}')
  edev=$(echo "$out" | awk '/e_dev/{print $3; exit}')
  vflat=$(echo "$out" | awk '/vflat/{print $3; exit}')
  idev=$(echo "$out" | awk '/idev/{print $3; exit}')
  awk -v wp="$WP" -v vf="$vflat" -v id="$idev" -v ed="$edev" -v ev="$evdd" 'BEGIN{
    ovh=(ed>0)?100*(ev-ed)/ed:0;
    printf "  %6s   %7.4f   %8.3f    %8.4f  %8.4f   %7.1f\n", wp, vf, id*1e3, ed*1e12, ev*1e12, ovh}'
done
