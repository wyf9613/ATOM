# Assignment 2 — Ethics

Yifan Wu · 1618332 · ENGR90037 · 2026 Semester 2

## 使用材料

| 文件 | 用途 |
| --- | --- |
| [ATOM_Ethics_Report.docx](ATOM_Ethics_Report.docx) | 可编辑的英文书面作业 |
| [ATOM_Ethics_Report.pdf](ATOM_Ethics_Report.pdf) | 同内容 PDF；两页正文加一页参考文献 |
| [ATOM_Ethics_Slides.html](ATOM_Ethics_Slides.html) | **主要展示文件**；按用户要求为 HTML，不生成 PowerPoint |
| [ATOM_Ethics_Slides.pdf](ATOM_Ethics_Slides.pdf) | HTML 的两页打印输出，方便预览或在接受 PDF 时留档 |
| [ATOM_Ethics_Speaker_Notes.md](ATOM_Ethics_Speaker_Notes.md) | 323 词简单英文讲稿，每句一行；也嵌在 HTML 的讲稿面板里 |
| [ATOM_Ethics_Speaker_Notes_Bilingual.md](ATOM_Ethics_Speaker_Notes_Bilingual.md) | 同一份简单讲稿的中英对照版，附关键词释义；建议先读 |
| [PREPARATION.md](PREPARATION.md) | 中文理解提示、课程对应表、18 个英文答辩回答及中文提示；不提交 |
| [ATOM_Ethics_Chinese_Guide.md](ATOM_Ethics_Chinese_Guide.md) | 中文答辩指南：核心论点、项目实例、两页 slides 讲述思路和八个重点追问；建议先读 |

HTML 双击打开即可，无需联网或启动服务。←／→ 或空格翻页，F 全屏，N 显示讲稿，Esc 收起讲稿，P 打印。全屏展示前关闭讲稿面板。打印只输出两页 slides，隐藏导航和讲稿。

## 作业约束检查

报告六部分按题目顺序排列。**正文加 AI 声明共 782 词**；额外按连字符、斜线等拆词计数为 797 词，仍低于 850 词。标题和参考文献不计入；没有脚注。具体计数见 [validation.json](validation.json)。

| 部分 | 当前词数 | 单项上限 |
| --- | ---: | ---: |
| Project and significance | 88 | 100 |
| Three stakeholder groups | 46 | 50 |
| Purpose | 40 | 50 |
| Three values and three principles | 189 | 200 |
| Goals, means and ends | 288 | 300 |
| Two code tenets | 117 | 150 |
| AI declaration | 14 | 已纳入总数 |

两页 slides，简单英文讲稿 323 词，每句最多 12 词，排练目标约 4:30；实际时长以本人计时为准，最多 5 分钟。AI 声明已同时加入报告和 slides，用一句话概括 AI 对构思、起草和修订的辅助。

已用本机 Chrome 验证键盘和按钮翻页、讲稿同步、三个窗口尺寸（含手机尺寸）、离线零网络请求及页面无内容溢出。HTML 打印输出为两页；报告 PDF 为三页。报告 DOCX 的全部正文、声明及参考文献与文字源逐段核对一致。原始 CSV 重新计算后生成图表，未改动原始数值。

## 提交安排与剩余核对

- Part 1：Week 11 周五 23:59 前，通过 Canvas Turnitin 提交书面作业；在 DOCX 和 PDF 中按提交页面要求选择，不必默认两份都上传。
- Part 2：Week 12 个人展示和答辩；展示最多 5 分钟、slides 最多两页，随后约 10 分钟 Q&A；展示后提交 slides。
- 原题明确写 PowerPoint。此处按用户要求制作 HTML；**HTML／PDF 是否被展示设备和 Canvas 接受，需要核对实际要求，未声称课程已经批准格式替代。** PDF 是打印输出，不是官方格式批准。
- Faculty／Capstone 的具体 AI 允许范围尚未提供。已核对课程要求必须披露所有 AI 使用，但不能据此推断完整 AI 起草已获许可；提交前按 Canvas 的实际规则核对和处理。
- 报告署名和学号由用户明确提供。最终观点、表述和项目事实应由本人核实、理解，并能在 Q&A 中解释。

不需要提交本 README、生成脚本、JSON、完整讲稿或答辩准备，除非 Canvas 另有要求。本地材料已完成，未上传 Canvas 或代为提交。

## 论证与证据

核心判断：有价值的目标必须通过可接受的手段实现，并关注可预见的正面和负面后果。用空载磁场变化说明证据局限如何约束自主程度，再分析收益与负担的分配。

职业守则使用课堂列出的 Consult Australia 第 7 条和 Engineers Australia 第 4.2 条。课程概念参考 Howard 的 PPE 最终讲义与 EE-4；Brey 的方法用于提前分析具体产物及使用情境。详细证据边界见 [EVIDENCE_AND_REVIEW.md](EVIDENCE_AND_REVIEW.md)。

## 源文件与重建

- `content.json`：报告及参考文献的文字源。
- `oral.json`：两页英文讲稿。
- `slides.template.html`：独立 HTML 模板。
- `build_materials.py`：读取以上源文件及五组原始 CSV，生成报告、HTML、讲稿、字数和证据统计；不打开串口、不驱动硬件、不上传文件。
- `evidence.json`：平台均值、样本 SD、ΔBz、条件和原始 CSV SHA-256。

在仓库根目录运行：

```sh
tmp/assignment2_ethics/venv/bin/python docs/assignment2/ethics/build_materials.py
```

依赖为 `python-docx`、`reportlab`；字体使用本机 Arial。重建脚本不自行导出 HTML 的 PDF；浏览器打印或本机 `tmp/assignment2_ethics/browser/validate.cjs` 可重新导出。PDF 已由仓库现有 `.gitattributes` 的 Git LFS 规则覆盖；未改动任何原始课件、历史报告或硬件文件。
