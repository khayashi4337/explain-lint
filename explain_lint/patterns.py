"""Extraction policy, ledger schema, and shared config.

The single source of truth for the constants used across explain-lint, so the
CLI, the MCP server, and the docs never drift out of sync (ISSUE-06).
"""
import re

# --- extraction policy (min lengths shared by scan() defaults and the CLI) ---
DEFAULT_MIN_KANA = 3   # a katakana run must be at least this long to count
DEFAULT_MIN_LATIN = 3  # a Latin word/abbreviation must be at least this long

KATAKANA = re.compile(r"[ァ-ヴー]+")
# A capitalized word, optionally joined by -/& to further capitalized parts, so
# `AT&T`, `R&D`, `Peacock-Hall`, `Runge-Kutta` are each one term. Individual
# parts may be a single letter (for `AT&T`); the whole match is length-filtered
# by min_latin, which drops stray "A"/"I" while letting short abbreviations
# through. Capitalized-only by design (lowercase jargon is out of scope here).
LATIN = re.compile(r"\b[A-Z][A-Za-z]*(?:[-&][A-Z][A-Za-z]*)*\b")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
# Spans stripped before term extraction (math, code, image, url carry no terms).
STRIP = [
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\$[^$\n]*\$"),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"https?://\S+|10\.\d{4,}/\S+"),
]

# --- ledger schema ---
HASH_LEN = 8                     # length of the line-content hash (hex chars)
HASH_RE = re.compile(rf"^[0-9a-f]{{{HASH_LEN}}}$")
PIPE_SPLIT = re.compile(r"(?<!\\)\|")  # split a table row on UNescaped pipes only
COLS = ["term", "category", "first_seen", "hash", "explained", "notes"]
TERMS_SUFFIX = ".terms.md"       # default ledger path = <first input> + this
DEFAULT_PREAMBLE = (
    "# explain-lint ledger\n\n"
    "- Machine-maintained first-occurrence table. explain-lint diffs the text\n"
    "  against this file; only NEW/MOVED terms need a fresh judgment.\n"
    "- Edit `category` / `explained` / `notes` by hand or with an LLM.\n"
    "- `first_seen` line numbers are auto-updated by `--sync`.\n\n"
)
