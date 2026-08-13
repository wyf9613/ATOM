# Project ATOM technical roadmap

This directory contains the LaTeX source for the literature-supported technical roadmap and implementation plan.

## Reviewed PDF

The reviewed 41-page A4 deliverable is stored at:

```text
output/pdf/ATOM_Technical_Roadmap.pdf
```

PDF files in this repository are managed by Git LFS. A freshly cloned or
partially downloaded workspace may contain a 131-byte text pointer instead of
the PDF. Restore this specific artifact from the repository root with:

```bash
git lfs install
git lfs pull --include="output/pdf/ATOM_Technical_Roadmap.pdf" --exclude=""
```

Verify the restored artifact with:

```bash
file output/pdf/ATOM_Technical_Roadmap.pdf
sha256sum output/pdf/ATOM_Technical_Roadmap.pdf
pdfinfo output/pdf/ATOM_Technical_Roadmap.pdf
```

Expected values for the reviewed artifact:

```text
Size:    344319 bytes
SHA-256: 7b88c014fce3c5b81d91d26a53df54d5d953452f62d1a07c5a312127073cb0de
Pages:   41
Format:  PDF 1.7, A4, not encrypted
```

## Build

Run from this directory:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

The bibliography uses `biblatex` and `biber`; `latexmk` runs the required passes automatically.

The reviewed deliverable is copied to `output/pdf/ATOM_Technical_Roadmap.pdf`.

The source requires a XeLaTeX distribution with `ctex`, TikZ, `biblatex` and
`biber`. Rebuilding is not necessary merely to replace an LFS pointer; pull the
reviewed binary first. If the document is rebuilt, inspect the complete log,
render all pages, and only replace the reviewed artifact after the page count,
fonts, references and visual layout have been checked.
