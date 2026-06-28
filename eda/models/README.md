# `eda/models/` — Verilog-A 器件紧凑模型

`smtj_sot.va`：三端 SOT-sMTJ 紧凑模型——SOT 写分支（$$R_\mathrm{SOT}=776\,\Omega$$）、MTJ 读分支
（$$R_P=4.9\,\mathrm{k}\Omega$$ / $$R_\mathrm{AP}=9.8\,\mathrm{k}\Omega$$）、事件驱动且显式种子的随机
切换（概率写与随机电报噪声两种模式）。暴露参数与第二章标定一致：`Vth=0.8958`、`VT=0.0234`、
`Delta=4.91`、`Vc0=0.857`、`tau0=1e-9`、`seed`。

编译与使用（详见 [`../SETUP_opensource.md`](../SETUP_opensource.md)）：用 OpenVAF 编译为 OSDI，由
ngspice 经 `.spiceinit` 的 `osdi smtj_sot.osdi` 调用。对金标准的回归见
[`../testbenches/run_regression.py`](../testbenches/run_regression.py)（$$R^2=1.0$$）。随机性由测试台
的 Python 环以显式种子驱动，不使用裸模拟瞬态噪声。
