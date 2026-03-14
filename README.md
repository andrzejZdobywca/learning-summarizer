# Learning Summarizer

A set of [Claude Code](https://claude.com/claude-code) skills, hooks, and a Python extraction script for reading and summarizing books (PDF/EPUB).

## Setup

1. Clone this repo
2. Drop your PDF or EPUB files into `content/`
3. Make sure `pdftotext` is available (for PDFs): `brew install poppler`

No Python dependencies beyond the standard library are needed.

## How it works

### Extract a table of contents

Use the `/extract-toc` skill or run the script directly:

```bash
python extract.py toc content/my-book.pdf            # scans first 30 pages
python extract.py toc content/my-book.pdf --pages 50  # scan more pages
python extract.py toc content/my-book.epub            # parses toc.ncx
```

This outputs a structured markdown TOC. The skill saves it to `content/<book>-table-of-contents.md`.

### Read specific chapters

Use the `/read-chapter` skill or run:

```bash
python extract.py chapter content/my-book.epub 1      # single chapter
python extract.py chapter content/my-book.pdf 5-8      # chapter range
```

### Auto-TOC hook

A `PreToolUse` hook is configured so that if Claude tries to read a raw book file (PDF/EPUB), the TOC is auto-generated first and Claude is prompted to read that instead. This prevents accidentally loading multi-megabyte files into context.

### Summarize workflow

Tell Claude what you read (e.g. "I read chapters 5-8 of The Prize") and it will:

1. Log it in `reading_log.md`
2. Extract the relevant chapters using `/read-chapter`
3. Generate a summary in `summaries/`

See `CLAUDE.md` for the full workflow details.

## File structure

```
├── extract.py                  # PDF/EPUB extraction script
├── CLAUDE.md                   # Claude Code workflow instructions
├── reading_log.md              # Reading progress log
├── content/                    # Place your books here
├── summaries/                  # Generated summaries
└── .claude/
    ├── settings.json           # Hook configuration
    ├── hooks/
    │   └── auto-toc.sh         # Auto-generates TOC on book read
    └── skills/
        ├── extract-toc/
        │   └── SKILL.md        # /extract-toc skill
        └── read-chapter/
            └── SKILL.md        # /read-chapter skill
```
