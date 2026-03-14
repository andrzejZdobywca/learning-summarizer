---
name: read-chapter
description: Extract and read specific chapters from a book (PDF/EPUB)
allowed-tools: Bash(python *)
argument-hint: "<book-filename> <chapter-range>"
---

# Read Chapter

Given a book filename and chapter range (e.g. `the-prize.epub 1-3` or `fabozzi-foundations-of-financial-markets.pdf 5`):

1. Run the extraction script:
   ```
   python books/extract.py chapter books/content/<book-filename> <chapter-range>
   ```

2. Display the extracted chapter text in chat.

The chapter range can be a single number (e.g. `5`) or a range (e.g. `1-3`).
