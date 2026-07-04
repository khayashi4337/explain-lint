"""
explain-lint — a linter for unexplained terms in (AI-written) prose.

WHY
    Compilers catch "undefined variable". Prose has the same bug: a term used
    without ever being explained. AI-generated text is especially prone to it —
    it drops jargon fluently and never defines it. explain-lint is the prose
    analogue of a linter: it finds every term's FIRST occurrence, remembers it
    in a ledger, and — differentially — surfaces only what changed since last
    time, so the expensive "is this explained?" judgment (by a human or an LLM)
    runs on the diff, not the whole document every time.

WHAT IT DOES (the machine-detection core — MVP)
    1. Extract candidate terms (katakana runs and/or Latin words).
    2. Record each term's FIRST occurrence: file, line, nearest heading, and a
       hash of that line's normalized text.
    3. Diff against a ledger:
         NEW   — term not in the ledger (needs a judgment)
         MOVED — first-occurrence line text changed (its context moved; re-judge)
         GONE  — in the ledger but no longer in the text
       Line-number drift alone (same hash, new line number) is NOT a change;
       `--sync` rewrites the numbers so real edits don't get buried in noise.

WHAT IT DOES NOT DO
    It does not decide whether a term is explained. That verdict — and the
    term's category — is a separate human/LLM layer written into the ledger's
    `category` / `explained` columns. The tool only keeps the ledger honest
    against the text and tells you what is new to judge.

LEDGER FORMAT (Markdown table; edit category/explained/notes by hand or LLM)
    | term | category | first_seen | hash | explained | notes |
    |---|---|---|---|---|---|
    | ホロノミー | needs-explanation | ch.md:42 §Geometry | ab12cd34 | no | ... |
    Suggested categories: needs-explanation / common / proper-noun / exclude
    Suggested explained:   yes / no / na

USAGE
    python explain_lint.py doc.md [more.md ...] [options]
      --ledger PATH   ledger file (default: <first-input>.terms.md)
      --report        (default) show NEW / MOVED / GONE; exit 1 if NEW or MOVED
      --dump          print every term's first occurrence (to seed a ledger)
      --sync          rewrite ledger line numbers for hash-matched terms
      --no-kana       do not extract katakana runs
      --no-latin      do not extract Latin words
      --min-kana N    minimum katakana run length (default 3)

    Typical first run:   python explain_lint.py doc.md --dump > seed.txt
    Then build the ledger, and thereafter:  python explain_lint.py doc.md

LICENSE  MIT.  Spun out of the "観測の窓" paper project (2026).
"""
import argparse
import hashlib
import os
import re
import sys

KATAKANA = re.compile(r"[ァ-ヴー]+")
LATIN = re.compile(r"\b[A-Z][A-Za-z]{2,}(?:[-&][A-Z][A-Za-z]+)*\b")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# Spans stripped before term extraction (math, code, links, urls keep no terms).
STRIP = [
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\$[^$\n]*\$"),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"https?://\S+|10\.\d{4,}/\S+"),
]

LEDGER_ROW = re.compile(
    r"^\|\s*(?P<term>[^|]+?)\s*\|\s*(?P<cat>[^|]*?)\s*\|"
    r"\s*(?P<seen>[^|]*?)\s*\|\s*(?P<hash>[0-9a-f]{8})\s*\|"
    r"\s*(?P<explained>[^|]*?)\s*\|\s*(?P<notes>[^|]*?)\s*\|"
)
LEDGER_HEADER = (
    "# explain-lint ledger\n\n"
    "- Machine-maintained first-occurrence table. `explain_lint.py` diffs the\n"
    "  text against this file; only NEW/MOVED terms need a fresh judgment.\n"
    "- Edit `category` / `explained` / `notes` by hand or with an LLM.\n"
    "- `first_seen` line numbers are auto-updated by `--sync`.\n\n"
    "| term | category | first_seen | hash | explained | notes |\n"
    "|---|---|---|---|---|---|\n"
)


def normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def line_hash(line: str) -> str:
    return hashlib.md5(normalize(line).encode("utf-8")).hexdigest()[:8]


def extract(paths, use_kana, use_latin, min_kana):
    """Return {term: (file, line_no, heading, hash, line_text)} for first occurrences."""
    first = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        fname = os.path.basename(path)
        heading = ""
        in_code = False
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
                terms |= set(LATIN.findall(clean))
            for t in terms:
                if t not in first:
                    first[t] = (fname, i, heading, line_hash(raw), raw.strip())
    return first


def load_ledger(path):
    entries = {}
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = LEDGER_ROW.match(line.rstrip())
            if m and m.group("term") not in ("term", ":---", "---"):
                entries[m.group("term")] = {
                    "cat": m.group("cat"), "seen": m.group("seen"),
                    "hash": m.group("hash"), "explained": m.group("explained"),
                    "notes": m.group("notes"),
                }
    return entries


def fmt_seen(fname, line, heading):
    return f"{fname}:{line}" + (f" §{heading}" if heading else "")


def main():
    ap = argparse.ArgumentParser(prog="explain-lint", description="Lint prose for unexplained terms.")
    ap.add_argument("inputs", nargs="+", help="Markdown/text file(s), in reading order")
    ap.add_argument("--ledger", help="ledger file (default: <first-input>.terms.md)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true", help="show NEW/MOVED/GONE (default)")
    mode.add_argument("--dump", action="store_true", help="print all first occurrences")
    mode.add_argument("--sync", action="store_true", help="update ledger line numbers (hash-matched)")
    ap.add_argument("--no-kana", action="store_true", help="skip katakana extraction")
    ap.add_argument("--no-latin", action="store_true", help="skip Latin-word extraction")
    ap.add_argument("--min-kana", type=int, default=3, help="min katakana run length (default 3)")
    args = ap.parse_args()

    ledger_path = args.ledger or (args.inputs[0] + ".terms.md")
    first = extract(args.inputs, not args.no_kana, not args.no_latin, args.min_kana)
    ordered = sorted(first.items(), key=lambda kv: (kv[1][0], kv[1][1]))

    if args.dump:
        print("term\tfirst_seen\thash\tline")
        for t, (fn, ln, hd, h, text) in ordered:
            print(f"{t}\t{fmt_seen(fn, ln, hd)}\t{h}\t{text[:100]}")
        print(f"\n# {len(first)} terms", file=sys.stderr)
        return

    ledger = load_ledger(ledger_path)

    if args.sync:
        if not os.path.exists(ledger_path):
            sys.exit(f"no ledger at {ledger_path} (seed one with --dump first)")
        with open(ledger_path, encoding="utf-8") as f:
            content = f.read()
        updated = 0
        for t, (fn, ln, hd, h, _) in first.items():
            e = ledger.get(t)
            if e and e["hash"] == h and e["seen"] != fmt_seen(fn, ln, hd):
                content = content.replace(f"| {e['seen']} | {h} |", f"| {fmt_seen(fn, ln, hd)} | {h} |")
                updated += 1
        with open(ledger_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[--sync] updated {updated} line-number(s) for hash-matched terms")
        return

    new, moved, ok = [], [], 0
    for t, (fn, ln, hd, h, text) in ordered:
        e = ledger.get(t)
        if e is None:
            new.append((t, fn, ln, hd))
        elif e["hash"] != h:
            moved.append((t, fn, ln, hd, e["seen"]))
        else:
            ok += 1
    gone = [t for t in ledger if t not in first]

    print(f"[explain-lint] {len(first)} terms / ledger {len(ledger)} / matched {ok}")
    if not ledger:
        print(f"  (no ledger at {ledger_path}; seed one:  python {os.path.basename(sys.argv[0])} "
              f"{args.inputs[0]} --dump)")
    if new:
        print(f"  NEW ({len(new)}) — need a judgment:")
        for t, fn, ln, hd in new[:60]:
            print(f"    {fmt_seen(fn, ln, hd)}: {t}")
        if len(new) > 60:
            print(f"    ... and {len(new) - 60} more")
    if moved:
        print(f"  MOVED ({len(moved)}) — first-occurrence context changed, re-judge:")
        for t, fn, ln, hd, old in moved[:40]:
            print(f"    {t}: {old} -> {fmt_seen(fn, ln, hd)}")
    if gone:
        print(f"  GONE ({len(gone)}) — in ledger, no longer in text: {', '.join(gone[:15])}")
    if not (new or moved):
        print("  OK no new or moved terms")
    if new or moved:
        sys.exit(1)


if __name__ == "__main__":
    main()
