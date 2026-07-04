"""Ledger read/write, indexing, and the judgment upsert.

The ledger is a Markdown table an LLM or human edits; this module keeps it
honest against the text and is the only writer of verdicts.
"""
import os
from typing import Optional

from .patterns import COLS, DEFAULT_PREAMBLE, HASH_RE, PIPE_SPLIT, TERMS_SUFFIX
from .extract import fmt_seen, scan


def default_ledger(paths) -> str:
    """The default ledger path for a set of inputs: <first input> + TERMS_SUFFIX.

    The single definition of the convention — the CLI and the MCP server both
    call this so the suffix is never hard-coded twice (ISSUE-06).
    """
    return paths[0] + TERMS_SUFFIX


def _split_row(line: str) -> Optional[list]:
    """Split a Markdown table row into unescaped cell values, or None if not a row.

    Splits on UNescaped `|` (so `\\|` inside a cell stays put), then restores
    `\\|` -> `|`. This is the read side of write_ledger's escaping — the two must
    stay symmetric (ISSUE-02: an escaped pipe used to break parsing and drop the
    whole row).
    """
    line = line.rstrip()
    if not (line.startswith("|") and line.endswith("|")):
        return None
    parts = PIPE_SPLIT.split(line)[1:-1]
    return [p.strip().replace(r"\|", "|") for p in parts]


def read_ledger(path: str):
    """Return (preamble_text, ordered_rows). rows are dicts keyed by COLS."""
    if not os.path.exists(path):
        return DEFAULT_PREAMBLE, []
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    rows, table_started, preamble_lines = [], False, []
    for line in raw.split("\n"):
        cells = _split_row(line)
        if cells and len(cells) == len(COLS) and HASH_RE.match(cells[3]):
            rows.append(dict(zip(COLS, cells)))
            table_started = True
        elif not table_started:
            is_header = cells == COLS
            is_sep = bool(cells) and all(c and set(c) <= set("-: ") for c in cells)
            if not (is_header or is_sep):
                preamble_lines.append(line)
    preamble = "\n".join(preamble_lines).rstrip("\n") + "\n\n"
    return (preamble if preamble.strip() else DEFAULT_PREAMBLE), rows


def index(rows) -> dict:
    return {r["term"]: r for r in rows}


def write_ledger(path: str, preamble: str, rows) -> None:
    def esc(v):
        # A table row is one line, so newlines are collapsed to spaces (lossy,
        # intentional); pipes are then escaped so the value round-trips through
        # read_ledger's _split_row (ISSUE-02).
        return (v or "").replace("\r", " ").replace("\n", " ").replace("|", r"\|")
    out = [preamble.rstrip("\n"), "",
           "| " + " | ".join(COLS) + " |",
           "|" + "|".join(["---"] * len(COLS)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(esc(r.get(c, "")) for c in COLS) + " |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def list_gaps(ledger_path: str) -> list:
    """Terms judged explained=no — the actionable output."""
    _, rows = read_ledger(ledger_path)
    return [r for r in rows if r.get("explained", "").strip().lower() == "no"]


def record_judgment(ledger_path: str, term: str, category=None, explained=None,
                    notes=None, paths=None, **scan_kw) -> str:
    """Upsert a term's verdict into the ledger.

    Creating a row for a term new to the ledger needs `paths` (to locate its
    first occurrence). On update, passing `paths` also re-syncs first_seen/hash
    so judging a MOVED term clears it (ISSUE-01). Returns
    "created" | "updated" | "error: ...".
    """
    preamble, rows = read_ledger(ledger_path)
    row = index(rows).get(term)
    if row is None:
        if not paths:
            return "error: new term needs paths to locate first occurrence"
        occ = scan(paths, **scan_kw).get(term)
        if not occ:
            return "error: term not found in given paths"
        row = {"term": term, "category": category or "",
               "first_seen": fmt_seen(occ["file"], occ["line"], occ["heading"]),
               "hash": occ["hash"], "explained": explained or "", "notes": notes or ""}
        rows.append(row)
        action = "created"
    else:
        if category is not None:
            row["category"] = category
        if explained is not None:
            row["explained"] = explained
        if notes is not None:
            row["notes"] = notes
        if paths:
            occ = scan(paths, **scan_kw).get(term)
            if occ:
                row["first_seen"] = fmt_seen(occ["file"], occ["line"], occ["heading"])
                row["hash"] = occ["hash"]
        action = "updated"
    write_ledger(ledger_path, preamble, rows)
    return action
