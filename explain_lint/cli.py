"""The command-line entry point (`python -m explain_lint` / `explain-lint`).

Presentation only: this is the one place that prints and formats. The core
(extract / ledger / diff) never prints, so it stays importable and testable.
"""
import argparse
import os
import sys

from .patterns import DEFAULT_MIN_KANA, DEFAULT_MIN_LATIN
from .extract import fmt_seen, scan
from .ledger import default_ledger, index, list_gaps, read_ledger
from .diff import diff, sync_linenumbers

PROG = "explain-lint"


def main() -> None:
    # Survive a non-UTF-8 console (e.g. Windows cp932): report/dump output uses
    # `—` and `§`, which would raise UnicodeEncodeError out-of-box (ISSUE-03).
    # Confined to the CLI entry point; the core functions never print.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass  # already-wrapped or non-reconfigurable stream (e.g. test capture)

    ap = argparse.ArgumentParser(prog=PROG, description="Lint prose for unexplained terms.")
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

    ledger_path = args.ledger or default_ledger(args.inputs)
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
        print(f"  (no ledger at {ledger_path}; seed one:  python -m explain_lint "
              f"{args.inputs[0]} --dump)")
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
