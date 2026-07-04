"""
explain-lint — a linter for unexplained terms in (AI-written) prose.

WHY
    Compilers catch "undefined variable." Prose has the same bug: a term used
    without ever being explained. AI-generated text is especially prone to it —
    it drops jargon fluently and never defines it. explain-lint is the prose
    analogue of a linter: it finds every term's FIRST occurrence, remembers it
    in a ledger, and — differentially — surfaces only what changed since last
    time, so the "is this explained?" judgment (by a human or an LLM) runs on
    the diff, not the whole document every time.

TWO LAYERS
    - Machine core (this file): deterministic, offline, dependency-free.
      Extraction, first-occurrence tracking, ledger diff, context lookup,
      ledger read/write. Usable as a CLI and as importable functions.
    - Judgment layer (a human, or an LLM — e.g. via the MCP server in
      explain_lint_mcp.py): decides each term's category / explained, and
      writes the verdict back with record_judgment(). NOT in this file.

LEDGER FORMAT (Markdown table; edit category/explained/notes by hand or LLM)
    | term | category | first_seen | hash | explained | notes |
    Suggested categories: needs-explanation / common / proper-noun / exclude
    Suggested explained:   yes / no / na
    The actionable output is `explained = no`: needed-but-missing glosses.

CLI
    python explain_lint.py doc.md [more.md ...] [--ledger PATH]
      (default)     report NEW / MOVED / GONE; exit 1 if NEW or MOVED
      --dump        print every term's first occurrence (to seed a ledger)
      --sync        rewrite ledger line numbers for hash-matched terms
      --gaps        list ledger terms marked explained=no
      --no-kana / --no-latin / --min-kana N / --min-latin N   tune extraction

LICENSE  MIT. Spun out of the "観測の窓" paper project (2026).
"""
import argparse
import hashlib
import os
import re
import sys

# ------------------------------------------------------------------ patterns
# Extraction policy, in one place (ISSUE-04). min lengths are the single source
# of truth for both the scan() defaults and the CLI defaults.
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
STRIP = [
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\$[^$\n]*\$"),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"https?://\S+|10\.\d{4,}/\S+"),
]
HASH_RE = re.compile(r"^[0-9a-f]{8}$")
PIPE_SPLIT = re.compile(r"(?<!\\)\|")  # split a table row on UNescaped pipes only
COLS = ["term", "category", "first_seen", "hash", "explained", "notes"]
DEFAULT_PREAMBLE = (
    "# explain-lint ledger\n\n"
    "- Machine-maintained first-occurrence table. `explain_lint.py` diffs the\n"
    "  text against this file; only NEW/MOVED terms need a fresh judgment.\n"
    "- Edit `category` / `explained` / `notes` by hand or with an LLM.\n"
    "- `first_seen` line numbers are auto-updated by `--sync`.\n\n"
)

# ------------------------------------------------------------------ helpers
def normalize(line):
    return re.sub(r"\s+", " ", line.strip())


def line_hash(line):
    return hashlib.md5(normalize(line).encode("utf-8")).hexdigest()[:8]


def fmt_seen(fname, line, heading):
    return f"{fname}:{line}" + (f" §{heading}" if heading else "")


# ------------------------------------------------------------------ core: scan
def scan(paths, use_kana=True, use_latin=True, min_kana=DEFAULT_MIN_KANA,
         min_latin=DEFAULT_MIN_LATIN):
    """Return {term: {file,line,heading,hash,text}} for each term's first occurrence."""
    first = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        fname = os.path.basename(path)
        heading, in_code = "", False
        for i, raw in enumerate(lines, 1):
            if raw.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            hm = HEADING.match(raw)
            if hm:
                heading = hm.group(2).strip()
            clean = raw
            for pat in STRIP:
                clean = pat.sub(" ", clean)
            terms = set()
            if use_kana:
                terms |= {t for t in KATAKANA.findall(clean) if len(t) >= min_kana}
            if use_latin:
                terms |= {t for t in LATIN.findall(clean) if len(t) >= min_latin}
            for t in terms:
                if t not in first:
                    first[t] = {"file": fname, "line": i, "heading": heading,
                                "hash": line_hash(raw), "text": raw.strip()}
    return first


# ------------------------------------------------------------------ core: context
def get_context(term, paths, window=2, **scan_kw):
    """First occurrence of `term` with `window` lines of surrounding context.

    Returns {term, first_seen, file, line, heading, hash, context:[{n,text}...],
    line_text} or None if the term never occurs.
    """
    occ = scan(paths, **scan_kw).get(term)
    if not occ:
        return None
    for path in paths:
        if os.path.basename(path) == occ["file"]:
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
            lo = max(1, occ["line"] - window)
            hi = min(len(lines), occ["line"] + window)
            ctx = [{"n": n, "text": lines[n - 1]} for n in range(lo, hi + 1)]
            return {"term": term, "first_seen": fmt_seen(occ["file"], occ["line"], occ["heading"]),
                    "file": occ["file"], "line": occ["line"], "heading": occ["heading"],
                    "hash": occ["hash"], "line_text": occ["text"], "context": ctx}
    return None


# ------------------------------------------------------------------ core: ledger
def _split_row(line):
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


def read_ledger(path):
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


def index(rows):
    return {r["term"]: r for r in rows}


def write_ledger(path, preamble, rows):
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


def list_gaps(ledger_path):
    """Terms judged explained=no — the actionable output."""
    _, rows = read_ledger(ledger_path)
    return [r for r in rows if r.get("explained", "").strip().lower() == "no"]


def record_judgment(ledger_path, term, category=None, explained=None, notes=None,
                    paths=None, **scan_kw):
    """Upsert a term's verdict into the ledger.

    If the term is new to the ledger, its first_seen/hash are computed from
    `paths` (required for a new row). Returns "created" | "updated" | "error:...".
    """
    preamble, rows = read_ledger(ledger_path)
    idx = index(rows)
    row = idx.get(term)
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
        # Re-sync position when the caller supplies paths, so judging a MOVED
        # term also acknowledges its new first-occurrence and clears MOVED
        # (ISSUE-01: without this the term stayed MOVED forever).
        if paths:
            occ = scan(paths, **scan_kw).get(term)
            if occ:
                row["first_seen"] = fmt_seen(occ["file"], occ["line"], occ["heading"])
                row["hash"] = occ["hash"]
        action = "updated"
    write_ledger(ledger_path, preamble, rows)
    return action


# ------------------------------------------------------------------ core: diff / sync
def diff(first, ledger_idx):
    """Return {new, moved, gone, matched} comparing scan output to a ledger index."""
    new, moved, matched = [], [], 0
    for t, occ in sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"])):
        e = ledger_idx.get(t)
        seen = fmt_seen(occ["file"], occ["line"], occ["heading"])
        if e is None:
            new.append({"term": t, "first_seen": seen, **occ})
        elif e["hash"] != occ["hash"]:
            moved.append({"term": t, "first_seen": seen, "was": e["first_seen"], **occ})
        else:
            matched += 1
    gone = [t for t in ledger_idx if t not in first]
    return {"new": new, "moved": moved, "gone": gone, "matched": matched}


def sync_linenumbers(paths, ledger_path, **scan_kw):
    """Rewrite first_seen for hash-matched terms whose line moved. Returns count."""
    preamble, rows = read_ledger(ledger_path)
    first = scan(paths, **scan_kw)
    updated = 0
    for r in rows:
        occ = first.get(r["term"])
        if occ and occ["hash"] == r["hash"]:
            seen = fmt_seen(occ["file"], occ["line"], occ["heading"])
            if seen != r["first_seen"]:
                r["first_seen"] = seen
                updated += 1
    if updated:
        write_ledger(ledger_path, preamble, rows)
    return updated


# ------------------------------------------------------------------ CLI
def main():
    # Survive a non-UTF-8 console (e.g. Windows cp932): report/dump output uses
    # `—` and `§`, which would raise UnicodeEncodeError out-of-box (ISSUE-03).
    # Confined to the CLI entry point; the core functions never print.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass  # already-wrapped or non-reconfigurable stream (e.g. test capture)
    ap = argparse.ArgumentParser(prog="explain-lint", description="Lint prose for unexplained terms.")
    ap.add_argument("inputs", nargs="+", help="Markdown/text file(s), in reading order")
    ap.add_argument("--ledger", help="ledger file (default: <first-input>.terms.md)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dump", action="store_true", help="print all first occurrences")
    mode.add_argument("--sync", action="store_true", help="update ledger line numbers")
    mode.add_argument("--gaps", action="store_true", help="list terms marked explained=no")
    ap.add_argument("--no-kana", action="store_true")
    ap.add_argument("--no-latin", action="store_true")
    ap.add_argument("--min-kana", type=int, default=DEFAULT_MIN_KANA)
    ap.add_argument("--min-latin", type=int, default=DEFAULT_MIN_LATIN)
    args = ap.parse_args()

    ledger_path = args.ledger or (args.inputs[0] + ".terms.md")
    kw = dict(use_kana=not args.no_kana, use_latin=not args.no_latin,
              min_kana=args.min_kana, min_latin=args.min_latin)

    if args.dump:
        first = scan(args.inputs, **kw)
        print("term\tfirst_seen\thash\tline")
        for t, o in sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"])):
            print(f"{t}\t{fmt_seen(o['file'], o['line'], o['heading'])}\t{o['hash']}\t{o['text'][:100]}")
        print(f"\n# {len(first)} terms", file=sys.stderr)
        return

    if args.sync:
        if not os.path.exists(ledger_path):
            sys.exit(f"no ledger at {ledger_path} (seed one with --dump first)")
        print(f"[--sync] updated {sync_linenumbers(args.inputs, ledger_path, **kw)} line-number(s)")
        return

    if args.gaps:
        gaps = list_gaps(ledger_path)
        print(f"[explain-lint] {len(gaps)} unexplained term(s) (explained=no):")
        for r in gaps:
            print(f"    {r['first_seen']}: {r['term']}  {('— ' + r['notes']) if r['notes'] else ''}")
        return

    first = scan(args.inputs, **kw)
    _, rows = read_ledger(ledger_path)
    d = diff(first, index(rows))
    print(f"[explain-lint] {len(first)} terms / ledger {len(rows)} / matched {d['matched']}")
    if not rows:
        print(f"  (no ledger at {ledger_path}; seed one:  python "
              f"{os.path.basename(sys.argv[0])} {args.inputs[0]} --dump)")
    if d["new"]:
        print(f"  NEW ({len(d['new'])}) — need a judgment:")
        for r in d["new"][:60]:
            print(f"    {r['first_seen']}: {r['term']}")
        if len(d["new"]) > 60:
            print(f"    ... and {len(d['new']) - 60} more")
    if d["moved"]:
        print(f"  MOVED ({len(d['moved'])}) — first-occurrence context changed, re-judge:")
        for r in d["moved"][:40]:
            print(f"    {r['term']}: {r['was']} -> {r['first_seen']}")
    if d["gone"]:
        print(f"  GONE ({len(d['gone'])}) — in ledger, not in text: {', '.join(d['gone'][:15])}")
    if not (d["new"] or d["moved"]):
        print("  OK no new or moved terms")
    if d["new"] or d["moved"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
