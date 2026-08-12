# Project ATOM technical roadmap

This directory contains the LaTeX source for the literature-supported technical roadmap and implementation plan.

## Build

Run from this directory:

```powershell
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

The bibliography uses `biblatex` and `biber`; `latexmk` runs the required passes automatically.

The reviewed deliverable is copied to `output/pdf/ATOM_Technical_Roadmap.pdf`.
