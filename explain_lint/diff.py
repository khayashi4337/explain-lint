"""The differential: compare a scan against the ledger; sync pure line drift."""
from typing import TypedDict

from .extract import fmt_seen, scan
from .ledger import read_ledger, write_ledger


class DiffResult(TypedDict):
    new: list
    moved: list
    gone: list
    matched: int


def diff(first, ledger_idx) -> DiffResult:
    """Compare scan output (first) to a ledger index -> {new, moved, gone, matched}.

    new:   term absent from the ledger (needs a judgment)
    moved: first-occurrence line text changed (hash differs) -> re-judge
    gone:  in the ledger but no longer in the text
    matched: count of unchanged, already-judged terms
    """
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


def sync_linenumbers(paths, ledger_path: str, **scan_kw) -> int:
    """Rewrite first_seen for hash-matched terms whose line moved. Returns count.

    Only pure line drift (hash still matches) is synced; a content change (hash
    differs) is a MOVED left for record_judgment, not silently rewritten.
    """
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
