# CLAUDE.md <!-- version: v1.2 -->

## Maintenance Rule

**Whenever this file is modified:**
1. Increment the version number in the `<!-- version: vX.Y -->` tag on line 1 (bump minor: v1.2 → v1.3, v1.4, etc. — only go to v2.0 if explicitly asked)
2. Commit with a descriptive message
3. The post-commit hook will auto-push to GitHub

---

## Project Objective

Convert clean, formatted DOCX files into both `.tex` (LaTeX) and `.lyx` (LyX) format for use in LyX.

## Core Principle

**You are a transcription worker, not a content generator.**

Your sole job is to faithfully convert the content of the input DOCX into LaTeX/LyX format. Do not:
- Add, infer, or rewrite any text
- Fill in missing content or "improve" phrasing
- Generate section summaries, captions, or explanations
- Produce any output that is not directly derived from the source DOCX

If something is unclear or missing in the source, flag it — do not invent a replacement.

### Input Source

Input DOCX files come from the `pdf-conversion` project (`/home/anirudh/pdf-conversion/`), which produces clean Word documents from EduRev teaching notes. The user manually pastes specific DOCX files into this folder — never auto-pull from pdf-conversion.

**Important:** Only process `.docx` files placed directly in `/home/anirudh/tex_output/`. Do not read from subdirectories.

### Input File Characteristics

The input DOCX files are already clean and properly formatted (produced by `convert_document_v4.py`):
- **Text:** Accessible via standard paragraph styles — Heading 1, Heading 2, Heading 3, Normal body
- **Font:** Times New Roman throughout, black color
- **Images:** Embedded in paragraphs, center-aligned
- **Tables:** Simple grid borders, 12pt Times New Roman cell text
- **No watermarks, no headers/footers, no hyperlinks, no MCQ blocks** — all stripped upstream

## Tool Chain

**pandoc** is the sole conversion tool. No python-docx needed — the input is already clean.

```bash
# Install on CachyOS / Arch
sudo pacman -S pandoc
```

### Pandoc Style Mapping

pandoc reads DOCX paragraph styles and maps them automatically:

| DOCX style | LaTeX / LyX output |
|------------|-------------------|
| Heading 1 | `\section` |
| Heading 2 | `\subsection` |
| Heading 3 | `\subsubsection` |
| Normal | body paragraph |
| Tables | LaTeX table environment |
| Bold runs | `\textbf{}` |
| Images | `\includegraphics{}` (extracted to `media/`) |

## Project Structure

```
tex_output/
├── convert.py         ← main script
├── requirements.txt   ← no pip deps (pandoc is system tool)
├── CLAUDE.md
├── output/            ← auto-created; one subfolder per document
│   └── <docname>/
│       ├── <docname>.tex
│       ├── <docname>.lyx
│       └── media/     ← extracted images
└── logs/              ← auto-created; timestamped per run
```

## Usage

```bash
# Convert all DOCX files in this folder
python convert.py

# Convert specific file(s)
python convert.py Chapter12.docx
python convert.py Chapter10.docx Chapter11.docx
```

## Implementation Notes

- Skip temp files matching `~$*.docx` (created by Word when a file is open)
- Two pandoc calls per file: one for `.tex` (with `--standalone`), one for `.lyx`
- Both calls use `--extract-media=output/<stem>/media` so images land in the right place
- Log to `logs/convert_YYYYMMDD_HHMMSS.log` and echo to terminal
- Output dir `output/<stem>/` is created if it does not exist

## Verification

1. Paste a DOCX from `/home/anirudh/pdf-conversion/output/` into this folder
2. Run `python convert.py`
3. Open `output/<name>/<name>.tex` — verify headings, body text, image references
4. Open `output/<name>/<name>.lyx` directly in LyX (File → Open)
5. Confirm images are in `output/<name>/media/` and referenced correctly
