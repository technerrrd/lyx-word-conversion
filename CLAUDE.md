# CLAUDE.md <!-- version: v1.6 -->

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
- **No watermarks, no headers/footers, no hyperlinks** — all stripped upstream
- **MCQ blocks are present** and must be formatted per the MCQ Rules section below

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

## MCQ Rules

### All formats
- **Strip all original option markers** — remove `(a)`, `(i)`, `1)`, `A.`, etc. from option text
- **NEVER wrap the option table in `\begin{center}`**
- The question itself is an `\item` in the enclosing `enumerate` block (see Numbering Rules)

### `.tex` format

Drop the options table immediately below `\item \textbf{<QUESTION>}` using exactly `\\[0.13cm]`:

```latex
\item \textbf{<QUESTION>}\\[0.13cm]
\begin{tabular}{@{}p{0.45\textwidth} p{0.45\textwidth}@{}}
$\square$ A) <OPTION_1> & $\square$ B) <OPTION_2> \\
$\square$ C) <OPTION_3> & $\square$ D) <OPTION_4>
\end{tabular}
```

### `.lyx` format

Use an `Enumerate` layout item for the question (bold via ERT), then embed the tabular as an ERT inset:

```
\begin_layout Enumerate
\begin_inset ERT
status open

\begin_layout Plain Layout
\backslash
textbf{<QUESTION>}
\backslash
\backslash
[0.13cm]
\end_layout

\end_inset

\begin_inset ERT
status open

\begin_layout Plain Layout
\backslash
begin{tabular}{@{}p{0.45
\backslash
textwidth} p{0.45
\backslash
textwidth}@{}}
\end_layout

\begin_layout Plain Layout
$
\backslash
square$ A) <OPTION_1> & $
\backslash
square$ B) <OPTION_2>
\backslash
\backslash

\end_layout

\begin_layout Plain Layout
$
\backslash
square$ C) <OPTION_3> & $
\backslash
square$ D) <OPTION_4>
\end_layout

\begin_layout Plain Layout
\backslash
end{tabular}
\end_layout

\end_inset

\end_layout
```

### Assertion-Reasoning Lock

Every Assertion-Reasoning pair **must** be followed by these exact fixed options — never alter the wording.

**`.tex` format:**

```latex
\item \textbf{Assertion (A):} <ASSERTION TEXT>\\[0.06cm]
\textbf{Reason (R):} <REASON TEXT>\\[0.13cm]
\begin{tabular}{@{}p{0.45\textwidth} p{0.45\textwidth}@{}}
$\square$ A) Both Assertion and Reason are correct; Reason is correct explanation. &
$\square$ B) Both Assertion and Reason are correct; Reason is NOT correct explanation. \\
$\square$ C) Assertion is correct; Reason is incorrect. &
$\square$ D) Assertion is incorrect; Reason is correct.
\end{tabular}
```

**`.lyx` format** — same ERT inset pattern as MCQ Rules above, with the fixed option strings hard-coded:

```
\begin_layout Enumerate
\begin_inset ERT
status open

\begin_layout Plain Layout
\backslash
textbf{Assertion (A):} <ASSERTION TEXT>
\backslash
\backslash
[0.06cm]
\backslash
textbf{Reason (R):} <REASON TEXT>
\backslash
\backslash
[0.13cm]
\end_layout

\end_inset

\begin_inset ERT
status open

\begin_layout Plain Layout
\backslash
begin{tabular}{@{}p{0.45
\backslash
textwidth} p{0.45
\backslash
textwidth}@{}}
\end_layout

\begin_layout Plain Layout
$
\backslash
square$ A) Both Assertion and Reason are correct; Reason is correct explanation. &
$
\backslash
square$ B) Both Assertion and Reason are correct; Reason is NOT correct explanation.
\backslash
\backslash

\end_layout

\begin_layout Plain Layout
$
\backslash
square$ C) Assertion is correct; Reason is incorrect. &
$
\backslash
square$ D) Assertion is incorrect; Reason is correct.
\end_layout

\begin_layout Plain Layout
\backslash
end{tabular}
\end_layout

\end_inset

\end_layout
```

## Numbering Rules

These rules apply as post-processing steps on the pandoc `.tex` output:

- **Strip all original numbering** from the source text — remove prefixes like `Q1`, `2.`, `1.1`, `(a)`, etc. that appear at the start of paragraphs. The enumerate environment provides the numbering.
- **Under every `\subsection{}`**, open a fresh `\begin{enumerate}` block immediately after the heading.
- **Before the next `\subsection{}` or `\section{}`**, close the block with `\end{enumerate}`.
- Each item in the block must be wrapped in `\item`.

**Example:**
```latex
\subsection{Forces}
\begin{enumerate}
  \item A body at rest remains at rest...
  \item Newton's second law states...
\end{enumerate}
\subsection{Motion}
\begin{enumerate}
  \item Velocity is defined as...
\end{enumerate}
```

## Subject-Specific Spacing Rules

### IF MATH

Do **not** add rules or large vertical spaces. Output items cleanly:

| Type | `.tex` | `.lyx` |
|------|--------|--------|
| Regular question | `\item \textbf{<QUESTION>}` | `Enumerate` layout, bold via `\series bold` |
| Fill in the blank | `\item \textbf{<TEXT> _________.}` | Same, underscores inline |
| True/False | `\item \textbf{<STATEMENT>} \hfill ________` | ERT for `\hfill ________` after bold text |

---

### IF SCIENCE

For every question that is **not** an MCQ or fill-in-the-blank, and where **no answer is provided** in the source text, append writing lines after the item.

**Short questions** — 1 rule line:

`.tex`:
```latex
\item \textbf{<QUESTION>}
\par \vspace{0.3cm} \noindent\rule{\linewidth}{0.4pt} \vspace{0.5cm}
```

`.lyx`:
```
\begin_layout Enumerate
\series bold
<QUESTION>
\series default

\begin_inset ERT
status open

\begin_layout Plain Layout
\backslash
par
\backslash
vspace{0.3cm}
\backslash
noindent
\backslash
rule{
\backslash
linewidth}{0.4pt}
\backslash
vspace{0.5cm}
\end_layout

\end_inset

\end_layout
```

**Long questions** — 3 rule lines:

`.tex`:
```latex
\item \textbf{<QUESTION>}
\par \vspace{0.3cm} \noindent\rule{\linewidth}{0.4pt}
\par \vspace{0.4cm} \noindent\rule{\linewidth}{0.4pt}
\par \vspace{0.4cm} \noindent\rule{\linewidth}{0.4pt} \vspace{0.5cm}
```

`.lyx`: same ERT pattern as short, repeated 3 times with matching `\vspace` values.

**Fill in the blank** (same for Math and Science):

`.tex`: `\item \textbf{<TEXT> _________.}`
`.lyx`: `Enumerate` layout, bold text, underscores inline

**True/False** (same for Math and Science):

`.tex`: `\item \textbf{<STATEMENT>} \hfill ________`
`.lyx`:
```
\begin_layout Enumerate
\series bold
<STATEMENT>
\series default

\begin_inset ERT
status open

\begin_layout Plain Layout
\backslash
hfill ________
\end_layout

\end_inset

\end_layout
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
