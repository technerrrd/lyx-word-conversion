#!/usr/bin/env python3
"""
convert.py — DOCX to LaTeX/LyX converter for pdf-conversion output files.

Usage:
    python convert.py                     # convert all .docx in current dir
    python convert.py Chapter1.docx       # convert specific file
    python convert.py Ch1.docx Ch2.docx   # multiple files
"""

import sys
import os
import re
import shutil
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# XML namespaces
# ---------------------------------------------------------------------------
W   = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WP  = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A   = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R   = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PIC = 'http://schemas.openxmlformats.org/drawingml/2006/picture'

# ---------------------------------------------------------------------------
# Font size → heading level (w:sz is in half-points)
# ---------------------------------------------------------------------------
SIZE_MAP = {
    32: 'section',       # 16pt
    28: 'subsection',    # 14pt
}

# Width scale choices for images (fraction of \textwidth)
SCALE_OPTIONS = [0.25, 0.40, 0.50, 0.60, 0.75]

def pick_scale(cx_emu: int) -> float:
    """Choose the closest \textwidth fraction from EMU width."""
    text_width_emu = 6.5 * 914400  # assume 6.5in text width
    ratio = cx_emu / text_width_emu
    return min(SCALE_OPTIONS, key=lambda s: abs(s - ratio))

# ---------------------------------------------------------------------------
# Noise / TOC detection
# ---------------------------------------------------------------------------
TOC_RE = re.compile(r'^\d+\.\s+\S')   # "1. Introduction", "2. What Do We Eat?"

def is_toc_line(text: str) -> bool:
    return bool(TOC_RE.match(text.strip()))

# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------
def tex_escape(text: str) -> str:
    """Escape LaTeX special characters."""
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&',  r'\&'),
        ('%',  r'\%'),
        ('$',  r'\$'),
        ('#',  r'\#'),
        ('{',  r'\{'),
        ('}',  r'\}'),
        ('~',  r'\textasciitilde{}'),
        ('^',  r'\^{}'),
        ('_',  r'\_'),
        ('₹',  r'\rupee~'),
        ('Rs.', r'\rupee~'),
        ('INR', r'\rupee~'),
    ]
    # Do backslash first, then rest
    result = text
    for old, new in replacements:
        if old == '\\':
            result = result.replace(old, new)
            break
    for old, new in replacements[1:]:
        result = result.replace(old, new)
    return result

# ---------------------------------------------------------------------------
# Parse DOCX
# ---------------------------------------------------------------------------
def parse_docx(docx_path: Path):
    """
    Returns list of elements in document order.
    Each element is a dict with keys:
      type: 'heading' | 'body' | 'image' | 'mcq_question'
      level: 'section' | 'subsection'  (headings only)
      text: str
      filename: str   (images only)
      scale: float    (images only)
    """
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
        try:
            rels_xml = z.read('word/_rels/document.xml.rels').decode('utf-8')
        except KeyError:
            rels_xml = '<Relationships/>'
        media_files = [f for f in z.namelist() if f.startswith('word/media/')]

    # Build rId → filename
    rid_map = {}
    for rel in ET.fromstring(rels_xml):
        rid = rel.get('Id', '')
        tgt = rel.get('Target', '')
        if 'media' in tgt:
            rid_map[rid] = Path(tgt).name

    root = ET.fromstring(xml)
    body = root.find(f'{{{W}}}body')

    raw = []   # list of (sz, text, image_fname, cx_emu)

    for para in body.findall(f'{{{W}}}p'):
        # --- font size ---
        sz_el = para.find(f'.//{{{W}}}sz')
        try:
            sz = int(sz_el.get(f'{{{W}}}val')) if sz_el is not None else 24
        except (TypeError, ValueError):
            sz = 24

        # --- text ---
        texts = [t.text for t in para.findall(f'.//{{{W}}}t') if t.text]
        text = ' '.join(texts).strip()

        # --- inline image ---
        blip = para.find(f'.//{{{A}}}blip')
        img_fname = None
        cx_emu = 0
        if blip is not None:
            rid = blip.get(f'{{{R}}}embed', '')
            img_fname = rid_map.get(rid)
            ext = para.find(f'.//{{{WP}}}extent')
            if ext is not None:
                try:
                    cx_emu = int(ext.get('cx', 0))
                except (TypeError, ValueError):
                    cx_emu = 0

        raw.append((sz, text, img_fname, cx_emu))

    # --- Skip TOC block ---
    # Find the first sz=32 paragraph (title), skip TOC lines after it,
    # then resume from the second sz=32 paragraph (first real section).
    in_toc = False
    past_toc = False
    elements = []
    seen_first_heading = False

    for sz, text, img_fname, cx_emu in raw:
        # Image always included
        if img_fname:
            scale = pick_scale(cx_emu)
            elements.append({'type': 'image', 'filename': img_fname,
                              'scale': scale, 'text': ''})
            continue

        if not text:
            continue

        level = SIZE_MAP.get(sz)

        # First sz=32 = document title → skip it and enter TOC zone
        if level == 'section' and not seen_first_heading:
            seen_first_heading = True
            in_toc = True
            continue  # skip title

        # In TOC zone: skip numbered TOC entries
        if in_toc:
            if is_toc_line(text):
                continue  # skip TOC line
            else:
                in_toc = False  # TOC ended

        # Classify
        if level == 'section':
            elements.append({'type': 'heading', 'level': 'section', 'text': text})
        elif level == 'subsection':
            elements.append({'type': 'heading', 'level': 'subsection', 'text': text})
        else:
            # MCQ question detection
            if text.startswith('Try yourself:') or text.startswith('Try yourself :'):
                question = re.sub(r'^Try yourself\s*:\s*', '', text).strip()
                elements.append({'type': 'mcq_question', 'text': question})
            else:
                elements.append({'type': 'body', 'text': text})

    return elements, rid_map, media_files

# ---------------------------------------------------------------------------
# Reconstruct paragraphs (join split lines)
# ---------------------------------------------------------------------------
def reconstruct_paragraphs(elements):
    """Join consecutive body lines that are continuations of the same paragraph."""
    out = []
    buf = None

    def flush():
        nonlocal buf
        if buf:
            out.append(buf)
            buf = None

    for el in elements:
        if el['type'] != 'body':
            flush()
            out.append(el)
            continue

        text = el['text']
        if buf is None:
            buf = dict(el)
        else:
            prev = buf['text']
            # Join if previous line doesn't end a sentence and current starts lowercase
            if (not prev.endswith(('.', ':', '?', '!'))
                    and (text and text[0].islower())):
                buf['text'] = prev + ' ' + text
            else:
                flush()
                buf = dict(el)

    flush()
    return out

# ---------------------------------------------------------------------------
# Group into MCQ blocks
# ---------------------------------------------------------------------------
def group_mcq_blocks(elements):
    """
    Detect MCQ blocks: mcq_question followed by exactly 4 body lines (options A-D).
    Returns new element list where MCQ blocks are collapsed into type='mcq'.
    """
    out = []
    i = 0
    while i < len(elements):
        el = elements[i]
        if el['type'] == 'mcq_question':
            # Collect next 4 body elements as options
            opts = []
            j = i + 1
            while j < len(elements) and len(opts) < 4:
                if elements[j]['type'] == 'body':
                    opts.append(elements[j]['text'])
                    j += 1
                else:
                    break
            if len(opts) == 4:
                out.append({'type': 'mcq', 'text': el['text'], 'options': opts})
                i = j
                continue
            else:
                # Not enough options — just treat as body
                out.append({'type': 'body', 'text': el['text']})
        else:
            out.append(el)
        i += 1
    return out

# ---------------------------------------------------------------------------
# LaTeX writer
# ---------------------------------------------------------------------------
TEX_PREAMBLE = r"""\documentclass[12pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{amssymb}
\usepackage{enumitem}
\usepackage{rupee}
\usepackage{geometry}
\geometry{margin=2.5cm}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}

\begin{document}
"""

def write_tex(elements, out_path: Path, media_dir: Path):
    lines = [TEX_PREAMBLE]
    in_enum = False
    current_level = None  # 'section' or 'subsection'

    def close_enum():
        nonlocal in_enum
        if in_enum:
            lines.append(r'\end{enumerate}' + '\n')
            in_enum = False

    def open_enum():
        nonlocal in_enum
        if not in_enum:
            lines.append(r'\begin{enumerate}' + '\n')
            in_enum = True

    for el in elements:
        t = el['type']

        if t == 'heading':
            close_enum()
            lvl = el['level']
            txt = tex_escape(el['text'])
            if lvl == 'section':
                lines.append(f'\\section{{{txt}}}\n')
            else:
                lines.append(f'\\subsection{{{txt}}}\n')
            current_level = lvl

        elif t == 'body':
            open_enum()
            txt = tex_escape(el['text'])
            lines.append(f'\\item \\textbf{{{txt}}}\n')

        elif t == 'mcq':
            open_enum()
            q = tex_escape(el['text'])
            opts = [tex_escape(o) for o in el['options']]
            lines.append(f'\\item \\textbf{{{q}}}\\\\[0.13cm]\n')
            lines.append(r'\begin{tabular}{@{}p{0.45\textwidth} p{0.45\textwidth}@{}}' + '\n')
            lines.append(f'$\\square$ A) {opts[0]} & $\\square$ B) {opts[1]} \\\\\n')
            lines.append(f'$\\square$ C) {opts[2]} & $\\square$ D) {opts[3]}\n')
            lines.append(r'\end{tabular}' + '\n')

        elif t == 'image':
            close_enum()
            fname = el['filename']
            scale = el['scale']
            img_rel = f'media/{fname}'
            lines.append('\\begin{figure}[h]\n')
            lines.append('\\centering\n')
            lines.append(f'\\includegraphics[width={scale}\\textwidth]{{{img_rel}}}\n')
            lines.append('\\end{figure}\n\n')

    close_enum()
    lines.append(r'\end{document}' + '\n')

    out_path.write_text(''.join(lines), encoding='utf-8')

# ---------------------------------------------------------------------------
# LyX writer
# ---------------------------------------------------------------------------
LYX_HEADER = """\
#LyX 2.3 created this file.
\\lyxformat 544
\\begin_document
\\begin_header
\\save_transient_properties true
\\origin unavailable
\\textclass article
\\use_default_options true
\\maintain_unincluded_children false
\\language english
\\language_package default
\\inputencoding auto
\\fontencoding global
\\font_roman "default" "default"
\\font_sans "default" "default"
\\font_typewriter "default" "default"
\\font_math "auto" "auto"
\\font_default_family default
\\use_non_tex_fonts false
\\font_sc false
\\font_osf false
\\font_sf_scale 100 100
\\font_tt_scale 100 100
\\use_microtype false
\\use_dash_ligatures true
\\graphics default
\\default_output_format default
\\output_sync 0
\\bibtex_command default
\\index_command default
\\paperfontsize 12
\\spacing single
\\use_hyperref false
\\papersize a4paper
\\use_geometry true
\\use_package amsmath 1
\\use_package amssymb 1
\\use_package cancel 1
\\use_package esint 1
\\use_package mathdots 1
\\use_package mathtools 1
\\use_package mhchem 1
\\use_package stackrel 1
\\use_package stmaryrd 1
\\use_package undertilde 1
\\cite_engine basic
\\cite_engine_type default
\\biblio_style plain
\\use_bibtopic false
\\use_indices false
\\paperorientation portrait
\\suppress_date false
\\justification true
\\use_refstyle 1
\\use_minted 0
\\index Index
\\shortcut idx
\\color #008000
\\end_index
\\leftmargin 2.5cm
\\topmargin 2.5cm
\\rightmargin 2.5cm
\\bottommargin 2.5cm
\\secnumdepth 3
\\tocdepth 3
\\paragraph_separation indent
\\paragraph_indentation default
\\is_math_indent 0
\\math_numbering_side default
\\quotes_style english
\\dynamic_quotes 0
\\papercolumns 1
\\papersides 1
\\paperpagestyle default
\\tracking_changes false
\\output_changes false
\\html_math_output 0
\\html_css_as_file 0
\\html_be_strict false
\\end_header

\\begin_body
"""

LYX_FOOTER = """\
\\end_body
\\end_document
"""

def lyx_escape(text: str) -> str:
    """Escape backslashes for LyX plain layout."""
    return text.replace('\\', '\\backslash\n')

def write_lyx(elements, out_path: Path, media_dir: Path):
    lines = [LYX_HEADER]
    in_enum = False

    def close_enum():
        nonlocal in_enum
        in_enum = False  # LyX Enumerate auto-closes at next non-Enumerate layout

    def ert(content: str) -> str:
        """Wrap content in an ERT inset."""
        return (
            '\\begin_inset ERT\nstatus open\n\n'
            '\\begin_layout Plain Layout\n'
            f'{content}\n'
            '\\end_layout\n\n'
            '\\end_inset\n\n'
        )

    for el in elements:
        t = el['type']

        if t == 'heading':
            close_enum()
            layout = 'Section' if el['level'] == 'section' else 'Subsection'
            lines.append(f'\\begin_layout {layout}\n')
            lines.append(f'{el["text"]}\n')
            lines.append('\\end_layout\n\n')

        elif t == 'body':
            in_enum = True
            lines.append('\\begin_layout Enumerate\n')
            lines.append('\\series bold\n')
            lines.append(f'{el["text"]}\n')
            lines.append('\\series default\n')
            lines.append('\\end_layout\n\n')

        elif t == 'mcq':
            in_enum = True
            q = el['text']
            opts = el['options']
            lines.append('\\begin_layout Enumerate\n')
            # Question bold + spacing via ERT
            q_ert = (
                f'\\backslash\ntextbf{{{q}}}\\backslash\n\\backslash\n[0.13cm]\n'
            )
            lines.append(ert(q_ert))
            # 2x2 tabular via ERT
            tab = (
                '\\backslash\nbegin{tabular}{@{}p{0.45\\backslash\ntextwidth} '
                'p{0.45\\backslash\ntextwidth}@{}}\n'
                f'$\\backslash\nsquare$ A) {opts[0]} & '
                f'$\\backslash\nsquare$ B) {opts[1]} \\backslash\n\\backslash\n\n'
                f'$\\backslash\nsquare$ C) {opts[2]} & '
                f'$\\backslash\nsquare$ D) {opts[3]}\n'
                '\\backslash\nend{tabular}\n'
            )
            lines.append(ert(tab))
            lines.append('\\end_layout\n\n')

        elif t == 'image':
            close_enum()
            fname = el['filename']
            scale_pct = int(el['scale'] * 100)
            lines.append('\\begin_layout Standard\n')
            lines.append('\\align center\n')
            lines.append('\\begin_inset Float figure\n')
            lines.append('placement h\nwide false\nsideways false\nstatus open\n\n')
            lines.append('\\begin_layout Plain Layout\n')
            lines.append('\\align center\n')
            lines.append('\\begin_inset Graphics\n')
            lines.append(f'\tfilename media/{fname}\n')
            lines.append(f'\twidth {scale_pct}text%\n')
            lines.append('\\end_inset\n\n')
            lines.append('\\end_layout\n\n')
            lines.append('\\end_inset\n\n')
            lines.append('\\end_layout\n\n')

    lines.append(LYX_FOOTER)
    out_path.write_text(''.join(lines), encoding='utf-8')

# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------
def extract_images(docx_path: Path, media_dir: Path, media_files: list):
    media_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx_path) as z:
        for f in media_files:
            fname = Path(f).name
            dest = media_dir / fname
            dest.write_bytes(z.read(f))

# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------
def convert(docx_path: Path, base_dir: Path, logger: logging.Logger):
    stem = docx_path.stem
    out_dir = base_dir / 'output' / stem
    out_dir.mkdir(parents=True, exist_ok=True)
    media_dir = out_dir / 'media'

    logger.info(f'Converting: {docx_path.name}')

    elements, rid_map, media_files = parse_docx(docx_path)
    elements = reconstruct_paragraphs(elements)
    elements = group_mcq_blocks(elements)

    extract_images(docx_path, media_dir, media_files)
    logger.info(f'  Extracted {len(media_files)} images to {media_dir}')

    tex_path = out_dir / f'{stem}.tex'
    write_tex(elements, tex_path, media_dir)
    logger.info(f'  Wrote {tex_path}')

    lyx_path = out_dir / f'{stem}.lyx'
    write_lyx(elements, lyx_path, media_dir)
    logger.info(f'  Wrote {lyx_path}')

    counts = {t: sum(1 for e in elements if e['type'] == t)
              for t in ('heading', 'body', 'mcq', 'image')}
    logger.info(f'  Elements: {counts}')
    return counts

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    base_dir = Path(__file__).parent
    logs_dir = base_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = logs_dir / f'convert_{ts}.log'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ]
    )
    logger = logging.getLogger(__name__)

    # Determine files to process
    if len(sys.argv) > 1:
        files = []
        for arg in sys.argv[1:]:
            p = Path(arg)
            if not p.is_absolute():
                p = base_dir / p
            if not p.exists():
                logger.error(f'File not found: {p}')
            elif p.suffix.lower() != '.docx':
                logger.error(f'Not a .docx file: {p}')
            else:
                files.append(p)
    else:
        files = [f for f in base_dir.glob('*.docx')
                 if not f.name.startswith('~$')]

    if not files:
        logger.info('No .docx files found.')
        return

    logger.info(f'Processing {len(files)} file(s)')
    for f in files:
        try:
            convert(f, base_dir, logger)
        except Exception as e:
            logger.error(f'Error converting {f.name}: {e}', exc_info=True)

    logger.info('Done.')

if __name__ == '__main__':
    main()
