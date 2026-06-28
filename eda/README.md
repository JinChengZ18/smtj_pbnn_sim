# `eda/` — 器件-电路验证层与回灌接口

本目录在开源工具链上把 `smtj_pbnn_sim` 的电路级数值从「数量级」升级为「提取值」，并把这些值
回灌主仿真器。器件用自写的 Verilog-A SOT-MTJ 紧凑模型（OpenVAF 编译为 OSDI、ngspice 调用），CMOS
外围用 SkyWater sky130 工艺；版图、寄生提取、规则检查与版图—原理图一致性分别由 Magic、Netgen、
KLayout 完成，原理图由 Xschem 导出。所有工具均无需商业许可证。

## 环境准备

工具链（ngspice + OpenVAF + sky130 + Magic/Netgen/KLayout/Xschem）的安装见
[`SETUP_opensource.md`](SETUP_opensource.md)。各 Python 脚本需要电路工具在 `PATH` 上；纯解析脚本
（写能量、SAR 电容能量等）只需 `python3 + numpy`。

## 复现各项结果

以下命令均在本目录下运行。

| 结果 | 命令 | 产出 |
|---|---|---|
| Verilog-A 模型对金标准回归 | `python testbenches/gen_golden.py && python testbenches/run_regression.py` | 86 点 DC 扫描，`max\|err\|≈3.5e-4`、$$R^2=1.0$$ |
| 写路径能量与交付电压 | `python testbenches/write_mc_harness.py` | 器件级 0.78 pJ / 端到端含驱动 ~0.8 pJ；`write_summary.json` |
| 写线 IR 压降（提取方块电阻） | 见 `extraction/writeline/README.md` | 各列高往返金属电阻占 776 Ω 比例 |
| StrongARM 灵敏放大失调/能量 | `python hero/run_offset_mc.py && python hero/sa_postlayout.py` | $$\sigma_\mathrm{off}=9.2$$ mV、判决能 ~48 fJ |
| 斜率匹配读出前端（在环验证） | `python hero/run_readout_frontend.py` | $$R_\mathrm{TI}=613\,\Omega$$、$$\sigma_\mathrm{pc}\approx2.5$$ |
| 电压型电阻串写-DAC | `python hero/run_write_dac.py` | 单调性、最低有效位、量程 |
| 列共享 SAR 电容阵列能量 | `python testbenches/sar_capdac_energy.py` | 各位电容开关能量上下界 |
| 期刊级原理图（图 6–10） | `wsl … bash hero/schematics/build_schematics.sh *.sch` | `*.png/svg/pdf`（详见 `hero/schematics/`） |

电路提取值经 `interface/load_tech_params.py` 注入主仿真器并重算每-MAC 与 MNIST PPA。

## 目录结构

```
eda/
├── README.md
├── SETUP_opensource.md        # 工具链安装与运行
├── models/smtj_sot.va         # Verilog-A SOT-MTJ 紧凑模型
├── testbenches/               # ngspice 回归、写路径、SAR 电容能量、瞬态波形
├── hero/                      # 读出/写-DAC 电路与版图；schematics/ 原理图导出
├── extraction/                # 提取的能量/面积/写线 IR 数据（YAML/CSV）
├── interface/                 # 把提取值回灌 smtj_pbnn_sim 的 Python 胶水
└── vendor/vgsot-sim/          # submodule：宏自旋 LLG 求解器（真值参考）
```

## 与主仿真器的接口

`smtj_pbnn_sim` 不依赖 `eda/`；`eda/` 单向地把提取值写入仿真器可读的配置或默认值。下表给出各占位项
与其提取替代的对应；其中读出能量与写线 IR 已折入仿真器默认值（`ppa/tech_params.py`、
`array/ir_drop.py`），使仿真器单独运行即得可信数值。

| `smtj_pbnn_sim` 中的项 | `eda/` 提供的提取值 | 状态 |
|---|---|---|
| `ppa/tech_params.py` 读出能量 `e_smtj_read` | sky130 StrongARM 灵敏放大判决能 48 fJ | 已折入默认值 |
| `array/ir_drop.py` 写线压降 | 提取方块电阻的阻性梯子解算 | 已折入（`experiments/20_write_ir_drop.py` 演示） |
| `ppa/reservoir_energy.py` ADC 能量 | StrongARM 比较器 + SAR 电容阵列 | 已折入默认值 |
| `ppa/tech_params.py` 写-DAC/计数器能量 | sky130 DAC/计数器 | 仍为数量级占位（待提取） |
| `device/` 行为 Sigmoid | `models/smtj_sot.va`（回归一致） | 双模型交叉验证 |

## 相关文档

- 勘误与物理标定：[`../.agents/errata.md`](../.agents/errata.md)、[`../docs/physics_grounding.md`](../docs/physics_grounding.md)
