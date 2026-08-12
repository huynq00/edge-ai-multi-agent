# Bộ nguồn LaTeX — Báo cáo đồ án CE2206

Toàn bộ báo cáo nằm trong **một file**: `bao-cao.tex` (preamble, bìa, chương 1–7, phụ lục, và `refs.bib` nhúng qua `filecontents*`).

## Biên dịch (pdfLaTeX)

Cần cài TeX Live / MacTeX / MiKTeX. Trên Overleaf: để Compiler = **pdfLaTeX** (mặc định).

```bash
cd reports/latex
latexmk -pdf bao-cao.tex
# hoặc:
pdflatex bao-cao.tex && bibtex bao-cao && pdflatex bao-cao.tex && pdflatex bao-cao.tex
```

PDF đầu ra: `reports/latex/bao-cao.pdf`.

## Ghi chú

- Điền thông tin bìa trong `bao-cao.tex` (các chỗ `\placeholder{...}`).
- Font: Latin Modern + encoding T5 (tiếng Việt), tương thích pdfLaTeX.
- Bản Markdown gốc: `reports/bao-cao-do-an.md`.
