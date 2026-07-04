"""explain-lint — a linter for unexplained terms in (AI-written) prose.

WHY
    Compilers catch "undefined variable." Prose has the same bug: a term used
    without ever being explained. AI-generated text is especially prone to it —
    it drops jargon fluently and never defines it. explain-lint is the prose
    analogue of a linter: it finds every term's FIRST occurrence, remembers it
    in a ledger, and — differentially — surfaces only what changed since last
    time, so the "is this explained?" judgment (by a human or an LLM) runs on
    the diff, not the whole document every time.

LAYERS (one concern per module)
    patterns  — extraction policy, ledger schema, shared config constants
    extract   — scan(), get_context(): find each term's first occurrence
    ledger    — read/write the Markdown ledger, record_judgment(), list_gaps()
    diff      — diff(), sync_linenumbers(): the differential
    cli       — the command-line entry point (the only module that prints)
    The judgment (is this term one that needs a gloss, and is it explained?) is
    a separate human/LLM layer — see explain_lint_mcp.py.

CLI
    python -m explain_lint doc.md [more.md ...] [--ledger PATH]
      (default)     report NEW / MOVED / GONE; exit 1 if NEW or MOVED
      --dump        print every term's first occurrence (to seed a ledger)
      --sync        rewrite ledger line numbers for hash-matched terms
      --gaps        list ledger terms marked explained=no
      --no-kana / --no-latin / --min-kana N / --min-latin N   tune extraction

LICENSE  MIT. Spun out of the "観測の窓" paper project (2026).
"""
from .patterns import (COLS, DEFAULT_MIN_KANA, DEFAULT_MIN_LATIN,
                       DEFAULT_PREAMBLE, HASH_LEN, HASH_RE, HEADING, KATAKANA,
                       LATIN, PIPE_SPLIT, STRIP, TERMS_SUFFIX)
from .extract import (Occurrence, fmt_seen, get_context, line_hash, normalize,
                      scan)
from .ledger import (default_ledger, index, list_gaps, read_ledger,
                     record_judgment, write_ledger)
from .diff import DiffResult, diff, sync_linenumbers
from .cli import main

__all__ = [
    # extraction
    "scan", "get_context", "normalize", "line_hash", "fmt_seen", "Occurrence",
    # ledger (the private _split_row lives at explain_lint.ledger._split_row)
    "read_ledger", "write_ledger", "index", "list_gaps", "record_judgment",
    "default_ledger",
    # diff
    "diff", "sync_linenumbers", "DiffResult",
    # cli
    "main",
    # config / patterns
    "DEFAULT_MIN_KANA", "DEFAULT_MIN_LATIN", "KATAKANA", "LATIN", "HEADING",
    "STRIP", "HASH_RE", "HASH_LEN", "PIPE_SPLIT", "COLS", "TERMS_SUFFIX",
    "DEFAULT_PREAMBLE",
]
