# Reading Companion

This directory is a lightweight reading companion. Books live in `content/`, reading progress is tracked in `reading_log.md`, and generated summaries go in `summaries/`.

## Workflows

### 1. Log what I read

When I tell you what I read (e.g., "I read chapters 5-8 of The Prize"), append an entry to `reading_log.md` under today's date:

```markdown
## YYYY-MM-DD
- **Book Title** (Author) — Chapters X-Y
```

- If today's date section already exists, add the entry under it.
- If a new date, add a new `## YYYY-MM-DD` heading at the bottom.

### 2. Summarize

When I ask you to summarize (after logging), do the following:

1. Check if `content/<book-stem>-table-of-contents.md` exists. If not, run `/extract-toc <book-filename>` first.
2. Use the TOC to identify which chapters to extract.
3. Run `/read-chapter <book-filename> <chapter-range>` to get the chapter text.
4. Generate a summary and save it to `summaries/YYYY-MM-DD.md` with this format:

```markdown
# Reading Summary — YYYY-MM-DD

## What I read
- **Book Title** — Chapters X-Y

## Quick Summary
2-3 sentence overview of the material.

## Key Concepts
- Concept 1 — brief explanation
- Concept 2 — brief explanation

## Key People
- **Person Name** — who they are and their role in the narrative
```

5. After saving the file, share the summary in chat so we can discuss it.

If multiple books were logged for the day, include sections for each.

### 3. Discuss

Use the generated summary in `summaries/` as context for follow-up conversation about the reading. If I ask questions about what I read, reference both the summary and the source material in `content/`.
