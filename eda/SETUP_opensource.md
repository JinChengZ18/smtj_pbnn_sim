# 开源 EDA 工具链安装与运行 (Windows)

P1 及之后的开源路线需要两件核心工具：**ngspice ≥ 43**（含 OSDI 接口）与
**OpenVAF-Reloaded**（把 Verilog-A 编译成 `.osdi`）。

> 钉死版本（勘误 N3）：`ngspice ≥ 43`、`OpenVAF-Reloaded`（OSDI 0.4）。
> 不要用原 OpenVAF（2023 末停维护）或 Xyce（未集成 OpenVAF/OSDI）。

### 本机安装状态（2026-06-26）

- ngspice 46：
  `C:\Users\Lenovo\AppData\Local\Programs\EDA\ngspice-46\Spice64\bin`
- OpenVAF-Reloaded `20260616-2-gc592eed6`：
  `C:\Users\Lenovo\AppData\Local\Programs\EDA\openvaf-reloaded-20260616-2-gc592eed6`
- 两个目录已加入**当前 Windows 用户**的 `PATH`。新开的 PowerShell/CMD/终端可在任意目录直接运行
  `ngspice`、`openvaf` 和 `openvaf-r`；这不是管理员级、所有用户共享的系统安装。
- 已执行 P1 回归：86 个 DC 扫描点，`max|err|=3.51e-4`、`R²=1.00000`，PASS。

## 1. ngspice (≥ 43)

- 下载：https://ngspice.sourceforge.io/download.html （Windows 64-bit 预编译包）。
- 解压后把 `Spice64\bin` 加入 `PATH`，验证：`ngspice --version`（应 ≥ 43）。
- 确认 OSDI：`ngspice` 交互里执行 `osdi`（或 `pre_osdi`）不报"unknown command"。

## 2. OpenVAF-Reloaded

- 仓库：https://github.com/OpenVAF/OpenVAF-Reloaded （或 release 页的预编译 `openvaf` 二进制）。
- 放到 `PATH`，验证：`openvaf --version`。
- 编译模型：`openvaf eda/models/smtj_sot.va -o smtj_sot.osdi`（在 `eda/testbenches/` 下运行，输出 `.osdi`）。

## 3. （后续阶段）CMOS PDK 与版图工具

- **sky130**（外围晶体管）：`open_pdks` / volare 安装 sky130A；ngspice 直接用其 SPICE 模型。
- **Xschem**（原理图）、**Magic**/**KLayout**（版图、PEX）：P3 起需要；P1 不需要。
- Windows 上以上三者建议走 **WSL2** 或 Linux 容器（原生 Windows 支持弱）。P1/P2 用纯 ngspice+OpenVAF 即可，不必先装。

## 4. 跑通 P1 回归（装好 1、2 后）

```bash
# 1) 生成/刷新金标准（纯 Python，已可运行）
python eda/testbenches/gen_golden.py

# 2) 编译 .va + 跑 ngspice + 对金标准断言 R^2>=0.99（自动）
python eda/testbenches/run_regression.py
```

`run_regression.py` 会自动：用 OpenVAF 编译 `smtj_sot.va` → `.osdi`，用 ngspice 跑
`regression_psw.spice` 的 DC 扫描，解析 `ngspice_psw.csv`，与 `golden_psw.csv` 比对
`V(psw)`，打印 `max|err|` 与 `R²`，PASS 条件 `max|err|<1e-3 且 R²≥0.99`。
工具缺失时它会打印本文件指引并优雅退出（不报错）。

## 5. 排错提示

- `pre_osdi` 报未知命令 → ngspice 版本 < 39 或非 OSDI 构建，换 ≥43 的官方包。
- OSDI 加载失败 → 确认 `openvaf` 与 ngspice 同为 64-bit；`.osdi` 与 `.spice` 同目录。
- `Unable to find definition of model` → OSDI 实例前需有
  `.model <model-name> <Verilog-A-module-type>`；本项目使用 `.model smtj_sot smtj_sot`。
- 观测节点 `v(psw)` 为空 → 个别 ngspice 构建对"只有电压源支路、无其它连接"的节点敏感，可在网表里给 `psw/tau/sinf` 各挂一个 `Rdummy psw 0 1e12` 高阻到地。
