"""
explain-lint MCP server — expose the deterministic core to an LLM client.

The machine core (explain_lint.py) finds each term's first occurrence and
diffs it against a ledger. The *judgment* — is this term one that needs a gloss,
and is it actually explained at first use? — is the LLM's job. This server is
the seam: it lets an assistant drive the linter.

Typical loop an assistant runs:
    1. lint_report(paths)                  -> which terms are NEW / MOVED
    2. get_term_context(term, paths)       -> read how each is introduced
    3. record_judgment(...)                -> write the verdict to the ledger
    4. list_gaps(ledger)                   -> report unexplained terms to the human

The server holds no model and makes no API calls; it stays deterministic and
offline. The intelligence is whatever client connects to it.

Run:  python explain_lint_mcp.py           (stdio transport)
Deps: pip install mcp        (the core, explain_lint.py, needs nothing)
"""
import os
from mcp.server.fastmcp import FastMCP

import explain_lint as core

mcp = FastMCP("explain-lint")


def _ledger_for(paths, ledger):
    return ledger or (paths[0] + ".terms.md")


@mcp.tool()
def lint_report(paths: list[str], ledger: str = "") -> dict:
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
    """
    ledger_path = _ledger_for(paths, ledger)
    first = core.scan(paths)
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
def get_term_context(term: str, paths: list[str], window: int = 2) -> dict:
    """Return a term's first occurrence with surrounding lines, to judge it.

    Use this when lint_report's line_text is not enough to decide whether the
    term is explained at first use. `window` is the number of lines before and
    after to include. Returns {found:false} if the term never occurs.
    """
    ctx = core.get_context(term, paths, window=window)
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
    paths:     required only when creating a row for a term not yet in the
               ledger (used to locate its first occurrence). Omit when updating.
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
def sync_ledger(paths: list[str], ledger: str = "") -> dict:
    """Rewrite ledger line numbers for terms whose line drifted (hash unchanged).

    Run after edits that only shift line numbers, so lint_report stays quiet
    about pure drift and flags only real context changes.
    """
    ledger_path = _ledger_for(paths, ledger)
    if not os.path.exists(ledger_path):
        return {"updated": 0, "error": f"no ledger at {ledger_path}"}
    return {"updated": core.sync_linenumbers(paths, ledger_path), "ledger": ledger_path}


@mcp.tool()
def dump_terms(paths: list[str]) -> dict:
    """List every term's first occurrence (seed material for a new ledger)."""
    first = core.scan(paths)
    items = sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"]))
    return {"count": len(first),
            "terms": [{"term": t, "first_seen": core.fmt_seen(o["file"], o["line"], o["heading"]),
                       "hash": o["hash"]} for t, o in items]}


if __name__ == "__main__":
    mcp.run()
