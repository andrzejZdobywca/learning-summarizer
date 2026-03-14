---
name: extract-toc
description: Extract table of contents from a book (PDF/EPUB) and save as a .md file in books/content/
allowed-tools: Bash(python *), Write, Read
argument-hint: "<book-filename>"
---

# Extract TOC

Given a book filename (e.g. `the-prize.epub` or `fabozzi-foundations-of-financial-markets.pdf`):

1. Run the extraction script:
   ```
   python books/extract.py toc books/content/<book-filename>
   ```

2. Save the output to `books/content/<book-stem>-table-of-contents.md` where `<book-stem>` is the filename without extension.

3. Print the TOC in chat so the user can see it.

If the file already exists, overwrite it with fresh output.
