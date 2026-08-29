# ATOM 技术路线 LaTeX 源码

本目录保存带文献依据的技术路线与实施计划源码。路线描述计划和建议，不代表功能已经实现。

## 已审核 PDF

文件：`output/pdf/ATOM_Technical_Roadmap.pdf`

- 大小：344,319 bytes；
- SHA-256：`7b88c014fce3c5b81d91d26a53df54d5d953452f62d1a07c5a312127073cb0de`；
- 41 页，A4，PDF 1.7，未加密。

PDF 使用 Git LFS。若克隆后只有约 131 bytes，先在仓库根目录运行：

```bash
git lfs install
git lfs pull --include="output/pdf/ATOM_Technical_Roadmap.pdf" --exclude=""
```

## 构建

在本目录运行：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

需要 XeLaTeX、`ctex`、TikZ、`biblatex` 和 `biber`。重新构建后必须检查完整日志、渲染全部页面，并确认页数、字体、引用和版面后才能替换已审核 PDF。
