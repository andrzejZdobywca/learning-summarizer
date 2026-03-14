#!/usr/bin/env python3
"""Extract table of contents and chapters from PDF/EPUB books.

Usage:
    python extract.py toc <book-file> [--pages N]
    python extract.py chapter <book-file> <range>

Examples:
    python extract.py toc books/content/fabozzi.pdf
    python extract.py toc books/content/the-prize.epub
    python extract.py chapter books/content/fabozzi.pdf 5
    python extract.py chapter books/content/the-prize.epub 1-3
"""

import argparse
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path


# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------

def _pdftotext(path: str, first: int, last: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-f", str(first), "-l", str(last), path, "-"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"pdftotext error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def _parse_pdf_toc(text: str) -> list[dict]:
    """Parse chapter lines from pdftotext output.

    Handles two formats:
    1. Single-line: "1. Introduction ... 1"
    2. Multi-line (Pearson custom library):
         1. Introduction
         Frank J. Fabozzi/...
         <blank>
         1
    """
    entries: list[dict] = []
    lines = text.splitlines()

    # First try single-line format
    for line in lines:
        m = re.match(r"^\s*(\d+)\.\s+(.+?)\s{2,}(\d+)\s*$", line)
        if m:
            entries.append({
                "chapter": int(m.group(1)),
                "title": m.group(2).strip(),
                "page": int(m.group(3)),
            })
        else:
            m2 = re.match(r"^\s*(Index)\s{2,}(\d+)\s*$", line)
            if m2:
                entries.append({
                    "chapter": None,
                    "title": m2.group(1),
                    "page": int(m2.group(2)),
                })

    if entries:
        return entries

    # Multi-line format: chapter heading, then author line, then blank, then page number
    # Find the "Table of Contents" marker and scan from there
    toc_start = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*Table of Contents\s*$", line):
            toc_start = i + 1
            break

    if toc_start is None:
        return entries

    # Track expected next chapter number to stop at false positives
    expected_ch = 1
    i = toc_start
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if m:
            chapter_num = int(m.group(1))
            title = m.group(2).strip()
            # Stop if chapter numbers go backwards (we've left the TOC)
            if entries and chapter_num < expected_ch:
                break
            # Look ahead for the page number (next standalone number within 5 lines)
            page = None
            for j in range(i + 1, min(i + 6, len(lines))):
                pm = re.match(r"^\s*(\d+)\s*$", lines[j])
                if pm:
                    page = int(pm.group(1))
                    break
            if page is not None:
                entries.append({
                    "chapter": chapter_num,
                    "title": title,
                    "page": page,
                })
                expected_ch = chapter_num + 1
        else:
            # Check for "Index" line (marks end of TOC)
            m2 = re.match(r"^\s*(Index)\s*$", line)
            if m2:
                for j in range(i + 1, min(i + 4, len(lines))):
                    pm = re.match(r"^\s*(\d+)\s*$", lines[j])
                    if pm:
                        entries.append({
                            "chapter": None,
                            "title": "Index",
                            "page": int(pm.group(1)),
                        })
                        break
                break  # Index is always last
        i += 1

    return entries


def pdf_toc(path: str, pages: int = 30) -> str:
    text = _pdftotext(path, 1, pages)
    entries = _parse_pdf_toc(text)
    if not entries:
        return f"No TOC entries found in first {pages} pages.\n"

    lines = [f"# Table of Contents\n"]
    for e in entries:
        if e["chapter"] is not None:
            lines.append(f"- **Chapter {e['chapter']}**: {e['title']} (p. {e['page']})")
        else:
            lines.append(f"- **{e['title']}** (p. {e['page']})")
    lines.append("")
    return "\n".join(lines)


def pdf_chapter(path: str, start_ch: int, end_ch: int) -> str:
    # First extract TOC to find page ranges
    toc_text = _pdftotext(path, 1, 30)
    entries = _parse_pdf_toc(toc_text)
    if not entries:
        print("Could not parse TOC to find chapter pages.", file=sys.stderr)
        sys.exit(1)

    # Find start and end pages
    start_page = None
    end_page = None
    for i, e in enumerate(entries):
        if e["chapter"] == start_ch:
            start_page = e["page"]
        if e["chapter"] == end_ch:
            # End page is the start of the next chapter minus 1
            if i + 1 < len(entries):
                end_page = entries[i + 1]["page"] - 1
            else:
                end_page = start_page + 50  # fallback

    if start_page is None:
        print(f"Chapter {start_ch} not found in TOC.", file=sys.stderr)
        sys.exit(1)
    if end_page is None:
        end_page = start_page + 50

    return _pdftotext(path, start_page, end_page)


# ---------------------------------------------------------------------------
# EPUB helpers
# ---------------------------------------------------------------------------

def _epub_toc_entries(path: str) -> list[dict]:
    """Parse toc.ncx from an EPUB and return structured entries."""
    ns = {"ncx": "http://www.daisy.org/z3986/2005/ncx/"}
    with zipfile.ZipFile(path) as zf:
        toc_data = zf.read("OEBPS/toc.ncx").decode("utf-8")

    root = ET.fromstring(toc_data)
    entries: list[dict] = []

    def walk(node, depth=0):
        for nav in node.findall("ncx:navPoint", ns):
            label_el = nav.find("ncx:navLabel/ncx:text", ns)
            content_el = nav.find("ncx:content", ns)
            label = label_el.text.strip() if label_el is not None and label_el.text else ""
            src = content_el.get("src", "") if content_el is not None else ""
            if label:
                entries.append({
                    "label": label,
                    "src": src,
                    "depth": depth,
                })
            walk(nav, depth + 1)

    nav_map = root.find("ncx:navMap", ns)
    if nav_map is not None:
        walk(nav_map)

    return entries


def _epub_chapter_files(path: str) -> list[str]:
    """Return ordered list of chapter content files from the EPUB."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    # Filter to Text/ content files, sorted
    text_files = sorted(
        [n for n in names if n.startswith("OEBPS/Text/ch") and n.endswith((".xhtml", ".html"))],
        key=lambda x: _chapter_sort_key(x),
    )
    return text_files


def _chapter_sort_key(filename: str):
    """Extract chapter number from filename for sorting."""
    m = re.search(r"ch(\d+)", filename)
    return int(m.group(1)) if m else 999


def _epub_chapter_number_to_files(path: str) -> dict[int, str]:
    """Map chapter numbers to their EPUB files."""
    entries = _epub_toc_entries(path)
    mapping: dict[int, str] = {}
    for e in entries:
        # Match "CHAPTER I", "CHAPTER 2", etc.
        m = re.match(r"CHAPTER\s+(\w+)", e["label"], re.IGNORECASE)
        if m:
            ch_str = m.group(1)
            ch_num = _parse_chapter_num(ch_str)
            if ch_num is not None and ch_num not in mapping:
                src = e["src"].split("#")[0]  # remove anchor
                if src and not src.startswith("OEBPS/"):
                    src = "OEBPS/" + src
                mapping[ch_num] = src
    return mapping


def _parse_chapter_num(s: str) -> int | None:
    """Parse a chapter number that might be arabic or roman."""
    # Try arabic first
    try:
        return int(s)
    except ValueError:
        pass
    # Try roman numerals
    roman = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
             "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13,
             "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18,
             "XIX": 19, "XX": 20}
    return roman.get(s.upper())


def epub_toc(path: str) -> str:
    entries = _epub_toc_entries(path)
    if not entries:
        return "No TOC entries found.\n"

    lines = ["# Table of Contents\n"]
    for e in entries:
        indent = "  " * e["depth"]
        src_file = e["src"].split("#")[0]
        lines.append(f"{indent}- {e['label']} (`{src_file}`)")
    lines.append("")
    return "\n".join(lines)


def epub_chapter(path: str, start_ch: int, end_ch: int) -> str:
    mapping = _epub_chapter_number_to_files(path)
    if not mapping:
        print("Could not find chapter mappings in EPUB.", file=sys.stderr)
        sys.exit(1)

    output_parts: list[str] = []
    with zipfile.ZipFile(path) as zf:
        for ch in range(start_ch, end_ch + 1):
            if ch not in mapping:
                print(f"Chapter {ch} not found in EPUB.", file=sys.stderr)
                continue
            filepath = mapping[ch]
            try:
                html = zf.read(filepath).decode("utf-8")
            except KeyError:
                print(f"File {filepath} not found in EPUB archive.", file=sys.stderr)
                continue
            text = strip_html(html)
            # Clean up excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            output_parts.append(text.strip())

    return "\n\n---\n\n".join(output_parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Extract TOC or chapters from PDF/EPUB books.")
    sub = parser.add_subparsers(dest="command", required=True)

    toc_parser = sub.add_parser("toc", help="Extract table of contents")
    toc_parser.add_argument("book", help="Path to PDF or EPUB file")
    toc_parser.add_argument("--pages", type=int, default=30,
                           help="Number of pages to scan for TOC (PDF only, default: 30)")

    ch_parser = sub.add_parser("chapter", help="Extract specific chapters")
    ch_parser.add_argument("book", help="Path to PDF or EPUB file")
    ch_parser.add_argument("range", help="Chapter number (e.g. 5) or range (e.g. 1-3)")

    args = parser.parse_args()
    book_path = args.book

    if not os.path.exists(book_path):
        print(f"File not found: {book_path}", file=sys.stderr)
        sys.exit(1)

    ext = Path(book_path).suffix.lower()

    if args.command == "toc":
        if ext == ".pdf":
            print(pdf_toc(book_path, args.pages))
        elif ext == ".epub":
            print(epub_toc(book_path))
        else:
            print(f"Unsupported format: {ext}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "chapter":
        # Parse range
        if "-" in args.range:
            parts = args.range.split("-", 1)
            start_ch, end_ch = int(parts[0]), int(parts[1])
        else:
            start_ch = end_ch = int(args.range)

        if ext == ".pdf":
            print(pdf_chapter(book_path, start_ch, end_ch))
        elif ext == ".epub":
            print(epub_chapter(book_path, start_ch, end_ch))
        else:
            print(f"Unsupported format: {ext}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
