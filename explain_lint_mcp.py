"""
explain-lint MCP server — expose the deterministic core to an LLM client.

The machine core (the explain_lint package) finds each term's first occurrence
and diffs it against a ledger. The *judgment* — is this term one that needs a
gloss, and is it actually explained at first use? — is the LLM's job. This
server is the seam: it lets an assistant drive the linter.

Typical loop an assistant runs:
    1. lint_report(paths)                  -> which terms are NEW / MOVED
    2. get_term_context(term, paths)       -> read how each is introduced
    3. record_judgment(...)                -> write the verdict to the ledger
    4. list_gaps(ledger)                   -> report unexplained terms to the human

The server holds no model and makes no API calls; it stays deterministic and
offline. The intelligence is whatever client connects to it.

Run:  python explain_lint_mcp.py           (stdio transport)
Deps: pip install mcp        (the explain_lint core needs nothing)
"""
import os
from mcp.server.fastmcp import FastMCP

import explain_lint as core

mcp = FastMCP("explain-lint")

# extraction defaults come from the core, so CLI and MCP stay symmetric (ISSUE-06)
_MK = core.DEFAULT_MIN_KANA
_ML = core.DEFAULT_MIN_LATIN


def _extract_kw(use_kana, use_latin, min_kana, min_latin):
    return dict(use_kana=use_kana, use_latin=use_latin,
                min_kana=min_kana, min_latin=min_latin)


@mcp.tool()
def lint_report(paths: list[str], ledger: str = "", use_kana: bool = True,
                use_latin: bool = True, min_kana: int = _MK,
                min_latin: int = _ML) -> dict:
    """Diff prose file(s) against the term ledger and report what changed.

    Call this FIRST. It returns the terms that need a judgment:
      - new:   terms absent from the ledger (judge each: does it need a gloss?
               is it glossed at first use?). Each item has term, first_seen,
               line_text so you can often judge without a second call.
      - moved: terms whose first-occurrence line was reworded — re-judge these.
      - gone:  terms in the ledger no longer found in the text.
      - matched: count of unchanged terms (already judged; skip them).

    paths: markdown/text files in reading order.
    ledger: ledger path (default: <first-path>.terms.md).
    use_kana/use_latin/min_kana/min_latin: extraction tuning (same as the CLI).
    """
    ledger_path = ledger or core.default_ledger(paths)
    first = core.scan(paths, **_extract_kw(use_kana, use_latin, min_kana, min_latin))
    _, rows = core.read_ledger(ledger_path)
    d = core.diff(first, core.index(rows))
    trim = lambda o: {"term": o["term"], "first_seen": o["first_seen"],
                      "line_text": o["text"]}
    return {
        "ledger": ledger_path,
        "counts": {"total": len(first), "ledger": len(rows), "matched": d["matched"],
                   "new": len(d["new"]), "moved": len(d["moved"]), "gone": len(d["gone"])},
        "new": [trim(o) for o in d["new"]],
        "moved": [{**trim(o), "was": o["was"]} for o in d["moved"]],
        "gone": d["gone"],
    }


@mcp.tool()
def get_term_context(term: str, paths: list[str], window: int = 2,
                     use_kana: bool = True, use_latin: bool = True,
                     min_kana: int = _MK, min_latin: int = _ML) -> dict:
    """Return a term's first occurrence with surrounding lines, to judge it.

    Use this when lint_report's line_text is not enough to decide whether the
    term is explained at first use. `window` is the number of lines before and
    after to include. Returns {found:false} if the term never occurs.
    """
    ctx = core.get_context(term, paths, window=window,
                           **_extract_kw(use_kana, use_latin, min_kana, min_latin))
    if ctx is None:
        return {"found": False, "term": term}
    return {"found": True, **ctx}


@mcp.tool()
def record_judgment(ledger: str, term: str, category: str = "", explained: str = "",
                    notes: str = "", paths: list[str] | None = None) -> dict:
    """Write a term's verdict to the ledger (create the row, or update it).

    category:  needs-explanation | common | proper-noun | exclude
    explained: yes | no | na    (`no` = needs a gloss and lacks one — the finding)
    notes:     short free text.
    paths:     needed to create a row for a term not yet in the ledger, and to
               re-sync a MOVED term's position on update. Omit for a pure
               verdict edit of an existing row.
    Returns {action: created|updated|error, detail}.
    """
    action = core.record_judgment(ledger, term, category=category or None,
                                  explained=explained or None, notes=notes or None,
                                  paths=paths)
    ok = action in ("created", "updated")
    return {"action": action if ok else "error", "detail": "" if ok else action,
            "ledger": ledger, "term": term}


@mcp.tool()
def list_gaps(ledger: str) -> dict:
    """List terms judged `explained = no` — the actionable output (missing glosses)."""
    gaps = core.list_gaps(ledger)
    return {"count": len(gaps),
            "gaps": [{"term": r["term"], "first_seen": r["first_seen"],
                      "notes": r["notes"]} for r in gaps]}


@mcp.tool()
def sync_ledger(paths: list[str], ledger: str = "", use_kana: bool = True,
                use_latin: bool = True, min_kana: int = _MK,
                min_latin: int = _ML) -> dict:
    """Rewrite ledger line numbers for terms whose line drifted (hash unchanged).

    Run after edits that only shift line numbers, so lint_report stays quiet
    about pure drift and flags only real context changes.
    """
    ledger_path = ledger or core.default_ledger(paths)
    if not os.path.exists(ledger_path):
        return {"updated": 0, "error": f"no ledger at {ledger_path}"}
    updated = core.sync_linenumbers(
        paths, ledger_path, **_extract_kw(use_kana, use_latin, min_kana, min_latin))
    return {"updated": updated, "ledger": ledger_path}


@mcp.tool()
def dump_terms(paths: list[str], use_kana: bool = True, use_latin: bool = True,
               min_kana: int = _MK, min_latin: int = _ML) -> dict:
    """List every term's first occurrence (seed material for a new ledger)."""
    first = core.scan(paths, **_extract_kw(use_kana, use_latin, min_kana, min_latin))
    items = sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"]))
    return {"count": len(first),
            "terms": [{"term": t, "first_seen": core.fmt_seen(o["file"], o["line"], o["heading"]),
                       "hash": o["hash"]} for t, o in items]}


if __name__ == "__main__":
    mcp.run()
