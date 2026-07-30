"""
Robust PDF extraction pipeline.

Strategy:
1. PyMuPDF (fitz) — primary extraction (fast, good for digital PDFs)
2. pdfplumber — fallback when PyMuPDF yields poor results
3. Multi-column detection and reordering
4. Header/footer removal via repeated-text detection
5. Table extraction as markdown pipe tables
6. Page markers for LLM page-reference capability
7. Text deduplication and cleaning

OCR is NOT included in this version (deferred to a future iteration).
"""

from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# ---------------------------------------------------------------------------
# Precompiled Regexes for Performance
# ---------------------------------------------------------------------------
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_SPACES_RE = re.compile(r'[^\S\n]+')
_NEWLINES_RE = re.compile(r'\n{3,}')
_DIGITS_RE = re.compile(r'\d+')
_WHITESPACE_RE = re.compile(r'\s+')
_NUMBER_RE = re.compile(r'^\d+[\.,]?\d*$')

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PageContent:
    """Extracted content from a single PDF page."""
    page_number: int          # 1-indexed
    text: str                 # cleaned body text (no tables)
    tables: list[str] = field(default_factory=list)   # tables as markdown
    headings: list[str] = field(default_factory=list)  # detected headings
    is_scanned: bool = False  # True if page appears to be a scanned image
    has_drawings: bool = False  # True if page has vector drawings (lines, rects)


@dataclass
class ExtractedDocument:
    """Full document extraction result."""
    pages: list[PageContent]
    full_text: str             # concatenated with page markers
    total_pages: int
    extraction_method: str     # "pymupdf" | "pdfplumber" | "mixed"
    has_tables: bool
    has_scanned_pages: bool


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Pages with fewer characters than this (and images) are treated as scanned
_MIN_TEXT_LENGTH = 50

# Header/footer zone: top/bottom fraction of page height
_HEADER_FOOTER_ZONE = 0.08

# Minimum frequency to consider text as a repeated header/footer
_HEADER_FOOTER_MIN_FREQ = 3

# Quality threshold: if this fraction of pages fail, try pdfplumber
_QUALITY_FAILURE_THRESHOLD = 0.30

# Page marker format
_PAGE_MARKER = "\n\n--- PAGE {n} ---\n\n"


# ---------------------------------------------------------------------------
# Multi-column detection and reordering
# ---------------------------------------------------------------------------

def _detect_multi_column(blocks: list[dict], page_width: float) -> bool:
    """
    Detect if a page uses a multi-column layout by analysing the x0
    positions of text blocks. If blocks cluster into 2+ distinct
    horizontal zones, the page is multi-column.
    """
    if len(blocks) < 4:
        return False

    # Collect x0 (left edge) of all text blocks
    x_positions = [b["x0"] for b in blocks if b.get("type") == 0]
    if len(x_positions) < 4:
        return False

    mid = page_width / 2
    left_count = sum(1 for x in x_positions if x < mid * 0.7)
    right_count = sum(1 for x in x_positions if x > mid * 0.6)

    # Both halves need substantial content to be multi-column
    return left_count >= 3 and right_count >= 3


def _reorder_columns(blocks: list[dict], page_width: float) -> list[dict]:
    """
    Reorder blocks from a multi-column layout into proper reading order:
    left column top-to-bottom, then right column top-to-bottom.
    """
    mid = page_width / 2

    left = [b for b in blocks if b.get("x0", 0) < mid * 0.8]
    right = [b for b in blocks if b.get("x0", 0) >= mid * 0.8]

    left.sort(key=lambda b: b.get("y0", 0))
    right.sort(key=lambda b: b.get("y0", 0))

    return left + right


# ---------------------------------------------------------------------------
# Header / footer detection
# ---------------------------------------------------------------------------

def _is_in_header_zone(block: dict, page_height: float) -> bool:
    """Check if a block is in the top header zone."""
    return block.get("y0", 0) < page_height * _HEADER_FOOTER_ZONE


def _is_in_footer_zone(block: dict, page_height: float) -> bool:
    """Check if a block is in the bottom footer zone."""
    return block.get("y1", 0) > page_height * (1 - _HEADER_FOOTER_ZONE)


def _detect_repeated_headers_footers(pages_blocks: list[list[dict]],
                                      page_heights: list[float]) -> set[str]:
    """
    Find text strings that appear in header/footer zones across many pages.
    These are recurring headers/footers that should be removed.
    """
    zone_texts: list[str] = []

    for blocks, page_h in zip(pages_blocks, page_heights):
        for b in blocks:
            if b.get("type") != 0:
                continue
            text = b.get("text", "").strip()
            if not text or len(text) > 200:
                continue
            if _is_in_header_zone(b, page_h) or _is_in_footer_zone(b, page_h):
                # Normalize: collapse whitespace, strip page numbers
                normalized = _DIGITS_RE.sub('#', text)
                normalized = _WHITESPACE_RE.sub(' ', normalized).strip()
                zone_texts.append(normalized)

    # Texts appearing on many pages are headers/footers
    counts = Counter(zone_texts)
    min_freq = min(_HEADER_FOOTER_MIN_FREQ, max(2, len(pages_blocks) // 3))
    return {t for t, c in counts.items() if c >= min_freq}


# ---------------------------------------------------------------------------
# Table extraction
# ---------------------------------------------------------------------------

def _table_to_markdown(table_data: list[list]) -> str:
    """Convert a 2D table (list of rows, each a list of cell strings) to markdown."""
    if not table_data or not table_data[0]:
        return ""

    # Clean cells
    cleaned = []
    for row in table_data:
        cleaned_row = []
        for cell in row:
            cell_text = str(cell) if cell is not None else ""
            cell_text = cell_text.replace("|", "\\|").replace("\n", " ").strip()
            cleaned_row.append(cell_text)
        cleaned.append(cleaned_row)

    # Normalize column count
    max_cols = max(len(row) for row in cleaned)
    for row in cleaned:
        while len(row) < max_cols:
            row.append("")

    # Build markdown
    lines = []
    # Header row
    lines.append("| " + " | ".join(cleaned[0]) + " |")
    # Separator
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    # Data rows
    for row in cleaned[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def _extract_tables_pymupdf(page: fitz.Page) -> list[str]:
    """Extract tables from a PyMuPDF page using find_tables()."""
    tables_md = []
    try:
        tabs = page.find_tables()
        for tab in tabs:
            data = tab.extract()
            if data and len(data) > 1:  # need at least header + 1 row
                md = _table_to_markdown(data)
                if md:
                    tables_md.append(md)
    except Exception:
        pass
    return tables_md


def _extract_tables_pdfplumber(page) -> list[str]:
    """Extract tables from a pdfplumber page."""
    tables_md = []
    try:
        tables = page.extract_tables()
        if tables:
            for table in tables:
                if table and len(table) > 1:
                    md = _table_to_markdown(table)
                    if md:
                        tables_md.append(md)
    except Exception:
        pass
    return tables_md


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

def _detect_headings_from_blocks(text_dict: dict) -> list[str]:
    """
    Detect headings by analysing font sizes from the page's text dict.
    Text spans with a font size significantly larger than the median are headings.
    """
    headings = []
    try:
        font_sizes = []
        spans_data = []

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    text = span.get("text", "").strip()
                    if text and size > 0:
                        font_sizes.append(size)
                        spans_data.append((size, text, span.get("flags", 0)))

        if not font_sizes:
            return headings

        median_size = statistics.median(font_sizes)
        heading_threshold = median_size * 1.15  # 15% larger than median

        for size, text, flags in spans_data:
            is_bold = bool(flags & 2 ** 4)  # bit 4 = bold
            if (size >= heading_threshold or is_bold) and len(text) > 3 and len(text) < 200:
                # Avoid table cell text or single words that happen to be bold
                if not _NUMBER_RE.match(text):
                    headings.append(text)
    except Exception:
        pass

    return headings


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def _clean_page_text(text: str) -> str:
    """
    Clean extracted text while preserving numeric values exactly.

    - Collapse excessive whitespace (but keep paragraph breaks)
    - Remove null bytes and control characters
    - Deduplicate identical consecutive lines
    """
    if not text:
        return ""

    # Remove null bytes and most control chars (keep \n, \t)
    text = _CONTROL_CHARS_RE.sub('', text)

    # Normalize various unicode spaces to regular space (but keep newlines)
    text = _SPACES_RE.sub(' ', text)

    # Deduplicate consecutive identical lines
    lines = text.split('\n')
    deduped = []
    prev = None
    for line in lines:
        stripped = line.strip()
        if stripped != prev:
            deduped.append(line)
            prev = stripped
        # Keep blank lines (paragraph separators) but not excessive ones
        elif stripped == "" and (not deduped or deduped[-1].strip() != ""):
            deduped.append(line)

    text = '\n'.join(deduped)

    # Collapse 3+ consecutive newlines into 2
    text = _NEWLINES_RE.sub('\n\n', text)

    return text.strip()


def _remove_header_footer_text(text: str, hf_patterns: set[str]) -> str:
    """Remove lines that match known header/footer patterns."""
    if not hf_patterns:
        return text

    lines = text.split('\n')
    filtered = []
    for line in lines:
        normalized = _DIGITS_RE.sub('#', line.strip())
        normalized = _WHITESPACE_RE.sub(' ', normalized).strip()
        if normalized not in hf_patterns:
            filtered.append(line)
    return '\n'.join(filtered)


# ---------------------------------------------------------------------------
# PyMuPDF extraction
# ---------------------------------------------------------------------------

def _extract_with_pymupdf(file_path: str) -> tuple[list[PageContent], list[list[dict]], list[float]]:
    """
    Primary extraction using PyMuPDF.
    Returns (pages, raw_blocks_per_page, page_heights) for header/footer analysis.
    """
    doc = fitz.open(file_path)
    pages: list[PageContent] = []
    all_blocks: list[list[dict]] = []
    page_heights: list[float] = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        page_heights.append(page_height)

        # Get text blocks: list of (x0, y0, x1, y1, "text", block_no, type)
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        raw_blocks = text_dict.get("blocks", [])

        # Convert to dicts with explicit keys for easier handling
        blocks = []
        for b in raw_blocks:
            block_dict = {
                "x0": b.get("bbox", [0])[0] if isinstance(b.get("bbox"), (list, tuple)) else b.get("x0", 0),
                "y0": b.get("bbox", [0, 0])[1] if isinstance(b.get("bbox"), (list, tuple)) else b.get("y0", 0),
                "x1": b.get("bbox", [0, 0, 0])[2] if isinstance(b.get("bbox"), (list, tuple)) else b.get("x1", 0),
                "y1": b.get("bbox", [0, 0, 0, 0])[3] if isinstance(b.get("bbox"), (list, tuple)) else b.get("y1", 0),
                "type": b.get("type", 0),
                "text": "",
            }
            # Extract text from lines/spans for text blocks
            if b.get("type") == 0:
                lines_text = []
                for line in b.get("lines", []):
                    span_texts = [span.get("text", "") for span in line.get("spans", [])]
                    lines_text.append("".join(span_texts))
                block_dict["text"] = "\n".join(lines_text)
            blocks.append(block_dict)

        all_blocks.append(blocks)

        # Detect multi-column and reorder if needed
        text_blocks = [b for b in blocks if b["type"] == 0]
        if _detect_multi_column(text_blocks, page_width):
            text_blocks = _reorder_columns(text_blocks, page_width)

        # Extract text in reading order
        page_text = "\n".join(b["text"] for b in text_blocks if b["text"].strip())

        # Check if page might be scanned (very little text but has images)
        image_blocks = [b for b in blocks if b["type"] == 1]
        is_scanned = len(page_text.strip()) < _MIN_TEXT_LENGTH and len(image_blocks) > 0

        # Extract tables
        tables_md = _extract_tables_pymupdf(page)

        # Detect drawings (indicating potential tables)
        has_drawings = bool(page.get_drawings())

        # Detect headings
        headings = _detect_headings_from_blocks(text_dict)

        pages.append(PageContent(
            page_number=page_idx + 1,
            text=page_text,
            tables=tables_md,
            headings=headings,
            is_scanned=is_scanned,
            has_drawings=has_drawings,
        ))

    doc.close()
    return pages, all_blocks, page_heights


# ---------------------------------------------------------------------------
# pdfplumber extraction (fallback)
# ---------------------------------------------------------------------------

def _extract_with_pdfplumber(file_path: str) -> list[PageContent]:
    """Fallback extraction using pdfplumber. Better for complex layouts."""
    if not HAS_PDFPLUMBER:
        return []

    pages: list[PageContent] = []

    with pdfplumber.open(file_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            # Extract text
            page_text = page.extract_text(
                x_tolerance=3,
                y_tolerance=3,
                layout=True,          # preserve spatial layout
            ) or ""

            # Extract tables
            tables_md = _extract_tables_pdfplumber(page)

            # Detect if scanned
            is_scanned = len(page_text.strip()) < _MIN_TEXT_LENGTH

            pages.append(PageContent(
                page_number=page_idx + 1,
                text=page_text,
                tables=tables_md,
                headings=[],  # pdfplumber doesn't provide font info as easily
                is_scanned=is_scanned,
            ))

    return pages


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

def _build_full_text(pages: list[PageContent]) -> str:
    """
    Concatenate all pages into a single text with page markers.
    Tables are inlined after the page's body text.
    """
    sections = []

    for page in pages:
        parts = [_PAGE_MARKER.format(n=page.page_number)]

        # Add headings context if available
        if page.headings:
            # Headings are already part of the body text, no need to duplicate
            pass

        # Body text
        if page.text.strip():
            parts.append(page.text.strip())

        # Tables
        for i, table in enumerate(page.tables, 1):
            parts.append(f"\n[Table {i} on Page {page.page_number}]\n{table}")

        sections.append("\n".join(parts))

    return "\n".join(sections).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_document(file_path: str) -> ExtractedDocument:
    """
    Extract structured content from a PDF file.

    Strategy:
    1. Try PyMuPDF first
    2. Detect and remove repeated headers/footers
    3. If quality is poor (many near-empty pages), fall back to pdfplumber
    4. Clean text, preserve numerics, deduplicate
    5. Assemble full text with page markers

    Args:
        file_path: Path to the PDF file.

    Returns:
        ExtractedDocument with structured page content and full text.
    """
    # --- Phase 1: PyMuPDF extraction ---
    pymupdf_pages, all_blocks, page_heights = _extract_with_pymupdf(file_path)

    # --- Phase 2: Header/footer detection and removal ---
    hf_patterns = _detect_repeated_headers_footers(all_blocks, page_heights)

    for page in pymupdf_pages:
        page.text = _remove_header_footer_text(page.text, hf_patterns)
        page.text = _clean_page_text(page.text)

    # --- Phase 3: Quality check — do we need pdfplumber? ---
    total = len(pymupdf_pages)
    failed = sum(1 for p in pymupdf_pages if len(p.text.strip()) < _MIN_TEXT_LENGTH and not p.is_scanned)
    scanned = sum(1 for p in pymupdf_pages if p.is_scanned)

    extraction_method = "pymupdf"
    final_pages = pymupdf_pages

    if total > 0 and (failed / total) > _QUALITY_FAILURE_THRESHOLD and HAS_PDFPLUMBER:
        # PyMuPDF is producing poor results — try pdfplumber
        plumber_pages = _extract_with_pdfplumber(file_path)

        if plumber_pages:
            # Compare total text yield
            pymupdf_total = sum(len(p.text) for p in pymupdf_pages)
            plumber_total = sum(len(p.text) for p in plumber_pages)

            if plumber_total > pymupdf_total * 1.2:
                # pdfplumber extracted significantly more text
                for page in plumber_pages:
                    page.text = _clean_page_text(page.text)
                final_pages = plumber_pages
                extraction_method = "pdfplumber"
            else:
                # Use PyMuPDF but merge in pdfplumber tables where PyMuPDF missed them
                for pymu_page, plumb_page in zip(pymupdf_pages, plumber_pages):
                    if not pymu_page.tables and plumb_page.tables:
                        pymu_page.tables = plumb_page.tables
                extraction_method = "mixed"

    # Also try pdfplumber for tables on pages where PyMuPDF found none (only on pages with vector drawings)
    if HAS_PDFPLUMBER and extraction_method == "pymupdf":
        pages_needing_tables = [p for p in final_pages if not p.tables and p.has_drawings]
        if pages_needing_tables:
            try:
                with pdfplumber.open(file_path) as pdf:
                    for page_content in pages_needing_tables:
                        idx = page_content.page_number - 1
                        if idx < len(pdf.pages):
                            plumber_tables = _extract_tables_pdfplumber(pdf.pages[idx])
                            if plumber_tables:
                                page_content.tables = plumber_tables
            except Exception:
                pass

    # --- Phase 4: Assemble ---
    full_text = _build_full_text(final_pages)
    has_tables = any(p.tables for p in final_pages)
    has_scanned = any(p.is_scanned for p in final_pages)

    return ExtractedDocument(
        pages=final_pages,
        full_text=full_text,
        total_pages=total,
        extraction_method=extraction_method,
        has_tables=has_tables,
        has_scanned_pages=has_scanned,
    )

