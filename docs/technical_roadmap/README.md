# Project ATOM technical roadmap

This directory contains the LaTeX source for the literature-supported technical roadmap and implementation plan.

## Build

Run from this directory:

```powershell
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

The bibliography uses `biblatex` and `biber`; `latexmk` runs the required passes automatically.

The reviewed deliverable is copied to `output/pdf/ATOM_Technical_Roadmap.pdf`.


## 2026-09-11 update (Version 0.2)

新增章节 [Phase 4 动态避障与感知方案](shared_workspace_perception.tex)，并纳入 `main.tex` 正文及参考文献。项目 Phase/Stage 4 为端到端演示；原技术工作包 P4 仍是感知，两套编号已明确区分。

- **Phase 4a：进入即停。** 三维占用监控、停止缓冲、失效停止、停止确认与锁存恢复；不依赖“必须识别为人”才触发。
- **Phase 4b：受约束绕行。** 停止重规划为中间对照，在线更新为完整目标；全臂/夹爪/持物碰撞检查，无路则等待，接触任务不横移。
- **感知试验建议：** 借用固定 RGB-D，RGB 标记定位架/仪器，深度检测占用；透明试管先用实测槽位几何与存在/偏移核验。相机型号及新增规划器均未冻结。
- **Waypoint：** 相机内外参 → 标记 → 工位/槽位 → 各动作 TCP 目标 → 规划链节偏移，包含时间、有效性、误差预算及拒绝条件。
- **研究索引：** [新增文献及用途](../RELATED_WORK.md#9-动态避障与感知路点研究补充2026-09-11)。

范围见 [PROJECT_SCOPE.md](../PROJECT_SCOPE.md)，计划顺序见 D-012，未确认输入见 A-012–A-016。本文更新不表示动态避障或相机定位已经实现。
