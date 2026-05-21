# CLAUDE.md <!-- version: v2.2 -->

## Maintenance Rule

**Whenever this file is modified:**
1. Increment the version number in the `<!-- version: vX.Y -->` tag on line 1 (bump minor: v2.1 → v2.2, v2.3, etc. — only bump the major version if explicitly asked)
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

### Subject Detection

Before beginning conversion, scan the document title, chapter heading, or metadata for subject indicators. If the subject is not immediately obvious, ask the user: **"Is this a Math or Science document?"** and wait for confirmation before applying subject-specific spacing rules.

### Input Source

Input DOCX files come from the `pdf-conversion` project (`/home/anirudh/pdf-conversion/`), which produces clean Word documents from EduRev teaching notes. The user manually pastes specific DOCX files into this folder — never auto-pull from pdf-conversion.

**Important:** Only process `.docx` files placed directly in `/home/anirudh/tex_output/`. Do not read from subdirectories.

### Input File Characteristics

The input DOCX files are clean and formatted (produced by `convert_document_v4.py`):
- **Text:** ALL paragraphs use `Normal` style — heading level is determined by **font size**, not style name
- **Font:** Times New Roman throughout, bold throughout — do **not** use bold as a heading indicator
- **Images:** Embedded inline in paragraphs, center-aligned
- **Tables:** Simple grid borders, 12pt Times New Roman cell text
- **No watermarks, no headers/footers, no hyperlinks** — all stripped upstream
- **MCQ blocks are present** and must be formatted per the MCQ Rules section below

## Tool Chain

**Custom Python XML parser** (`convert.py`) reads `word/document.xml` directly from the DOCX ZIP.
Pandoc is not used — it cannot reconstruct heading hierarchy because all paragraphs are `Normal` style.

### Font Size → Structure Mapping

`convert.py` maps font size (`<w:sz>` half-points) to document structure:

| Font size (`w:sz`) | Point size | LaTeX output | LyX layout |
|--------------------|------------|--------------|------------|
| 32 | 16pt | `\section{}` | `Section` |
| 28 | 14pt | `\subsection{}` | `Subsection` |
| 24 | 12pt | body paragraph | `Enumerate` |
| other | varies | body paragraph | `Enumerate` |

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

---

## Numbering Rules

- **Strip all original numbering** from the source text — remove prefixes like `Q1`, `2.`, `1.1`, `(a)`, etc. that appear at the start of paragraphs. The enumerate environment provides the numbering.
- **Under every subsection**, open a fresh enumerate block immediately after the heading.
- **Before the next subsection or section**, close the enumerate block.
- Each item must be wrapped appropriately for the format.

**`.tex` example:**
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

**`.lyx` example:** In LyX, consecutive `Enumerate` layout items automatically form a list. The list resets naturally when a new `Subsection` layout begins — no explicit open/close needed.

```
\begin_layout Subsection
Forces
\end_layout

\begin_layout Enumerate
A body at rest remains at rest...
\end_layout

\begin_layout Enumerate
Newton's second law states...
\end_layout

\begin_layout Subsection
Motion
\end_layout

\begin_layout Enumerate
Velocity is defined as...
\end_layout
```

---

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

**`.lyx` format:**

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

---

## Subject-Specific Spacing Rules

### Short vs Long Question Detection

The source document will explicitly label sections as **"Long Question Answers"** or **"Short Question Answers"** — use that heading to determine which spacing to apply. For **case-based questions** (explicitly stated as such in the question text), treat as Short Question or MCQ as the question itself indicates.

### IF MATH

Do **not** add rules or large vertical spaces. Output items cleanly:

| Type | `.tex` | `.lyx` |
|------|--------|--------|
| Regular question | `\item \textbf{<QUESTION>}` | `Enumerate` layout, bold via `\series bold` |
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
par
\backslash
vspace{0.4cm}
\backslash
noindent
\backslash
rule{
\backslash
linewidth}{0.4pt}
\backslash
par
\backslash
vspace{0.4cm}
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

**Fill in the blank** (applies to both Math and Science):

`.tex`: `\item \textbf{<TEXT> _________.}`
`.lyx`: `Enumerate` layout, bold text, underscores inline

**True/False** (applies to both Math and Science):

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

---

## Math & Currency Lock

- **Math:** Wrap all mathematical expressions, variables, and equations in `$...$` (inline) or `$$...$$` (display block). Do NOT wrap plain numeric text like years, counts, or page numbers — only wrap values that are part of a mathematical context (e.g. `$x = 3$`, `$F = ma$`).
- **Currency:** Convert all ₹, Rs., and INR occurrences to `\rupee~<amount>` (e.g. ₹250 → `\rupee~250`).
- **No image transcription:** You are strictly forbidden from transcribing text or formulas found inside an image. **Exception:** tables inside images may be transcribed — see Table Transcription Exception below.

**`.lyx` math format:**

Inline math:
```
\begin_inset Formula $<MATH>$
\end_inset
```

Display math:
```
\begin_inset Formula 
$$<MATH>$$
\end_inset
```

---

## Automated Image Numbering & Smart Scaling

Pandoc extracts images and names them automatically (`image1.png`, `image2.jpeg`, etc.). **Do not rename them.** Map each image to its pandoc-assigned filename in the order they appear in the source.

**Sizing:** Read the rendered display size from the DOCX XML (`<wp:extent cx="..." cy="..."/>`, in EMUs where 914400 EMU = 1 inch). Use that to pick the closest width from: `0.25`, `0.4`, `0.5`, `0.6`, `0.75`. Do not use raw pixel dimensions.

**`.tex` figure block (exact format — no `\caption{}`):**
```latex
\begin{figure}[h]
\centering
\includegraphics[width=<CHOSEN_SCALE>\textwidth]{<pandoc-assigned-filename>}
\end{figure}
```

**`.lyx` figure block (no caption):**
```
\begin_inset Float figure
placement h
wide false
sideways false
status open

\begin_layout Plain Layout
\align center
\begin_inset Graphics
	filename media/<pandoc-assigned-filename>
	width <SCALE>text%
\end_inset

\end_layout

\end_inset
```

Scale mapping for `.lyx`: `0.25` → `25text%`, `0.4` → `40text%`, `0.5` → `50text%`, `0.6` → `60text%`, `0.75` → `75text%`

---

## No Image Hallucination

- **Never** insert a `\begin{figure}` block (`.tex`) or `\begin_inset Float figure` block (`.lyx`) for an image that does not exist in the source document.
- Only reference images that are explicitly present in the user-provided source text.

---

## Table Transcription Exception (Sync Lock)

You are allowed to transcribe tables (including those originally presented as images) into standard LaTeX `tabular` environments.

---

## Answer/Solution Exception

If the source text contains `Ans:`, `Answer:`, or `Solution:`, treat it as provided content. Place it immediately after the question item, on a new paragraph.

**`.tex`:**
```latex
\par \textit{Ans: <TRANSCRIPT_CONTENT>}
```

**`.lyx`:**
```
\begin_layout Standard

\shape italic
Ans: <TRANSCRIPT_CONTENT>
\shape default

\end_layout
```

**Critical:** Do **not** append writing lines (`\rule`) or `\vspace` when an answer is already present in the source.

---

## Rule Priority Order

When multiple rules could apply to the same content, use this precedence (highest wins):

1. **Answer/Solution Exception** — answer present in source → no writing lines, ever
2. **MCQ format** — question has A/B/C/D options → use MCQ grid, no writing lines
3. **Fill-in-the-blank** — question has blanks → use underscores, no writing lines
4. **Case-based question** — explicitly stated → follow Short/Long as indicated in the question itself
5. **Section heading** — "Long Question Answers" / "Short Question Answers" heading in source
6. **Subject default** — Math: no lines; Science: short = 1 rule line, long = 3 rule lines

---

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

---

## Required LaTeX Packages

Add these to your document preamble in LyX via **Document → Settings → LaTeX Preamble**:

| Package | Required for |
|---------|-------------|
| `graphicx` | `\includegraphics{}` in figure blocks |
| `rupee` | `\rupee` currency symbol |
| `amssymb` | `$\square$` checkbox in MCQ grids |
