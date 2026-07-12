# `eda/hero/layout/` — sky130 版图与提取流程（StrongARM SA + 2T SOT-sMTJ 单元）

| 文件 | 作用 |
|---|---|
| `gen_sa_layout.py` | KLayout-Python 生成器：以带保护环的 sky130 PCell（`nmos18`/`pmos18`）实例化 StrongARM 的 11 个晶体管（对照 `../strongarm_sa_core.spice`），展平并写出 GDS |
| `sa_devices.gds` | 输出 GDS（顶层单元 `strongarm_sa_devs`，23.1×18.7 µm，11 器件，sky130 图层） |
| `gen_2t_cell.py` | **2T SOT-sMTJ 单元生成器**（MTJ 计划 L1）：写管 nmos18 w=2.2 + 读管 nmos18 w=0.42（R180 置放）+ ptap 体接触条 + 纯脚本布线（via1/met2/via2/met3 + met1 延伸；PCell 已自带 S/D 与栅极的 li1+mcon+met1）+ 抽象 BEOL 黑盒；含全层 5-dbu 网格吸附（修 PCell 在部分 w 下的 0.001 µm 偏格怪癖） |
| `cell2t.gds` | 输出 GDS（顶层单元 `cell2t_smtj`；设计层 bbox 5.60×4.06 µm = 22.7 µm²，全 bbox 含标记层 27.4 µm²） |
| `cell2t_summary.json` | 单元几何/面积/pitch 口径 + 黑盒规格（生成器写出） |
| `check_layers.sh` | 黑盒层空位核查（sky130A.lyp + magic tech 中 ≥128 仅 235/4 被占用） |
| `run_drc.sh` / `run_drc_2t.sh` | sky130 DRC（`sky130A_mr.drc`）——**必须传特性开关**，见下 |
| `mk_drc_control.py` | DRC 阳性对照：向 cell2t.gds 注入已知 met1 宽度违例产出 `cell2t_control.gds`——deck 调用若对它报 0 即为假阴性，勿采信任何 0 违例结论 |
| `render_2t.py` | 无 GUI 的 GDS 顶视渲染（`QT_QPA_PLATFORM=offscreen klayout -z -nc -r render_2t.py`）→ `figures/panels/ch04_22_a.png`（sky130 lyp 配色 + 黑盒层高亮） |
| `run_pex.sh` / `run_pex_2t.sh` | Magic 寄生提取（`gds read → extract → ext2spice`） |
| `LVS_GUI_CHECKLIST.md` | SA 互连 / LVS 的逐网连接表与步骤 |

运行（WSL，`Ubuntu-24.04-EDA`）：

```bash
klayout -b -r gen_2t_cell.py        # 生成 cell2t.gds + cell2t_summary.json
bash run_drc_2t.sh                  # DRC（feol+beol+offgrid；0 违例，经阳性对照验证）
bash run_pex_2t.sh                  # 提取：2 FET（w=2.2/0.42）+ ~3.1 fF 寄生 C
```

## ⚠️ DRC 特性开关（2026-07-08 教训，勿再犯）

`sky130A_mr.drc` 的规则段包在 `$feol/$beol/$offgrid/$seal/$floating_met` 开关里，**不传开关时一条规则都不执行、恒报 0 违例**（假阴性）。正确调用必须带 `-rd feol=1 -rd beol=1 -rd offgrid=1`（seal=密封环规则不适用于单元；floating_met 会按设计逻辑标记黑盒连接的浮空金属岛，仅作参考跑）。每次换 deck/换调用方式，先做**阳性对照**（注入一个已知违例确认能被抓到）再采信 0。

**由此更正历史记录**：2026-06-26 的「SA 器件级 DRC 0 违例」是无开关调用的假阴性；带开关重跑 `sa_devices.gds` 实得 ~542 条——绝大多数为 `*_OFFGRID`（PCell 在保护环/部分 w 下生成 0.001 µm 偏格坐标），实质规则违例为 `m1.5`（mcon 的 met1 相邻边包络 0.06）×24 与 `li.3`（li 间距 0.17）×6，均属 PCell 压线/偏格伪影而非设计错误，与 2T 单元同类、可由全层 5-dbu 网格吸附修复（`gen_2t_cell.py` 已内置；SA 的修复随 1.7 布线窗口做）。SA 的寄生提取数（35.25 fF 等）不受影响（偏格 ±1 dbu 对电容无有效数字级影响）。

## 2T 单元的抽象 BEOL 黑盒（不可制造声明）

sky130A 无任何 MRAM/MTJ 模块，MTJ/SOT 层在版图中以**注记性 GDS 层**表示，仅声明连接、不可制造：

| 层 | GDS | 内容 | 几何锚（公开文献） |
|---|---|---|---|
| MTJ 柱包络 | **200/0** | 0.08 µm 方包络 | CD≈80 nm，Hikstor EDL 2024（DOI 10.1109/LED.2024.3454609） |
| SOT track | **201/0** | 0.20 µm 宽 | track 宽 200 nm、底电极间距 200 nm，同上 |

插层位置 met2–met3：BE 焊盘/SL 在 met2（与写线 met2+ 设计规则耦合），TE/读线在 met3。Magic techfile 不认识 200/201 → 提取时明确忽略（`pex2t.log` 有 "Unknown layer" 记录），CMOS 部分提取不受影响；提取网表中 BE2/SL 岛按设计浮空（连接只经黑盒，`**FLOATING` 注记如实）。层空位经 `check_layers.sh` 对 lyp+magic tech 双重核查。

面积口径（`cell2t_summary.json`）：设计层 bbox 22.7 µm²（含单元级 WWL/RWL/WBL/SL/RBL/BODY 存根与独立 ptap 条，未做阵列摊销/紧缩）；`a_smtj_cell=4.6 µm²` 的设计规则估算假设阵列上下文摊销（共享 tap、邻接布线）——实绘单元从上方界定该估算。剖面示意图 `figures/cell2t_cross_section.{png,svg}`（`eda/gen_cell2t_cross_section.py`）。

其余注意事项：DRC/PEX 在持久化 ext4 构建目录运行（WSL `/tmp` 空闲停机被清空）；LVS 用 Tim Edwards 的 netgen 而非 apt 的网格生成器。
