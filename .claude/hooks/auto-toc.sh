#!/usr/bin/env bash
# PreToolUse hook: auto-generate TOC when Claude tries to read a book file.
# Reads JSON from stdin, checks if the file is a book in books/content/.
# If no TOC exists, generates one and suggests reading it instead.

set -euo pipefail

# Read the hook input JSON from stdin
INPUT=$(cat)

# Extract the file_path from the tool input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
# The tool input is in data['tool_input']['file_path']
print(data.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null || echo "")

# Bail if no file path
[ -z "$FILE_PATH" ] && exit 0

# Check if this is a book file in books/content/
case "$FILE_PATH" in
    */books/content/*.pdf|*/books/content/*.epub) ;;
    *) exit 0 ;;
esac

# Get the book stem (filename without extension)
BASENAME=$(basename "$FILE_PATH")
STEM="${BASENAME%.*}"
BOOK_DIR=$(dirname "$FILE_PATH")
TOC_FILE="${BOOK_DIR}/${STEM}-table-of-contents.md"

# If TOC already exists, nothing to do
[ -f "$TOC_FILE" ] && exit 0

# Generate the TOC
# Find the repo root by looking for books/extract.py relative to the book dir
REPO_ROOT=$(cd "$BOOK_DIR/.." && pwd)
EXTRACT_SCRIPT="${REPO_ROOT}/extract.py"

if [ ! -f "$EXTRACT_SCRIPT" ]; then
    exit 0
fi

python3 "$EXTRACT_SCRIPT" toc "$FILE_PATH" > "$TOC_FILE" 2>/dev/null

if [ -f "$TOC_FILE" ]; then
    echo "Auto-generated TOC at ${TOC_FILE}. Consider reading the TOC file instead of the full book: ${STEM}-table-of-contents.md" >&2
fi

exit 0
