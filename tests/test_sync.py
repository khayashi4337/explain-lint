"""ISSUE-05: sync_linenumbers behaviour.

Pure line drift (same line text, new line number) is noise: sync rewrites the
number so it stays quiet. A real content change (hash differs) is a MOVED and
must NOT be silently synced — that needs a re-judgment (ISSUE-01).
"""
import explain_lint as e

TERM = "オブザーバブル"


def _seed(tmp_path, text):
    doc = tmp_path / "d.md"
    doc.write_text(text, encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), TERM, explained="no", paths=[str(doc)])
    return doc, ledger


def test_sync_updates_line_on_pure_drift(tmp_path):
    doc, ledger = _seed(tmp_path, f"# H\n\nThe {TERM} here.\n")
    _, rows = e.read_ledger(str(ledger))
    old_seen = e.index(rows)[TERM]["first_seen"]  # d.md:3 §H

    # prepend blank lines: the term's line MOVES but its TEXT (hash) is identical
    doc.write_text(f"\n\n\n# H\n\nThe {TERM} here.\n", encoding="utf-8")
    n = e.sync_linenumbers([str(doc)], str(ledger))

    assert n == 1
    _, rows = e.read_ledger(str(ledger))
    new_seen = e.index(rows)[TERM]["first_seen"]
    assert new_seen != old_seen
    assert new_seen.startswith("d.md:6")  # shifted down by 3 lines


def test_sync_ignores_content_change(tmp_path):
    doc, ledger = _seed(tmp_path, f"# H\n\nThe {TERM} here.\n")
    _, rows = e.read_ledger(str(ledger))
    old_hash = e.index(rows)[TERM]["hash"]
    old_seen = e.index(rows)[TERM]["first_seen"]

    # Move the line (prepend) AND reword it. The line moved, so a naive sync
    # would rewrite first_seen — but the hash changed, so the hash guard must
    # skip it. Moving the line is what makes n==0 a real regression for the
    # guard (a same-line reword would pass n==0 for the wrong reason).
    doc.write_text(f"\n\n\n# H\n\nThe {TERM} now reworded.\n", encoding="utf-8")
    n = e.sync_linenumbers([str(doc)], str(ledger))

    assert n == 0, "content change must not be silently synced, even if the line moved"
    _, rows = e.read_ledger(str(ledger))
    assert e.index(rows)[TERM]["hash"] == old_hash  # left for record_judgment to handle
    assert e.index(rows)[TERM]["first_seen"] == old_seen  # not rewritten
    # and it should still surface as MOVED for a re-judgment
    d = e.diff(e.scan([str(doc)]), e.index(rows))
    assert any(x["term"] == TERM for x in d["moved"])


def test_sync_noop_when_nothing_moved(tmp_path):
    doc, ledger = _seed(tmp_path, f"# H\n\nThe {TERM} here.\n")
    assert e.sync_linenumbers([str(doc)], str(ledger)) == 0
