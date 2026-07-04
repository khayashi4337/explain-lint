"""ISSUE-01 regression: a term's diff state must transition correctly.

NEW -> record_judgment -> matched (no longer NEW)
reword first occurrence -> MOVED -> record_judgment(paths) -> matched (MOVED clears)

The MOVED-clears case fails on the pre-fix code: record_judgment's update branch
never refreshed first_seen/hash, so a re-judged MOVED term stayed MOVED forever.
"""
import explain_lint as e

TERM = "オブザーバブル"


def _diff(doc, ledger):
    first = e.scan([str(doc)])
    _, rows = e.read_ledger(str(ledger))
    return e.diff(first, e.index(rows))


def test_new_then_judge_becomes_matched(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text(f"# H\n\nThe {TERM} appears here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"

    d = _diff(doc, ledger)
    assert any(x["term"] == TERM for x in d["new"]), "should start as NEW"

    e.record_judgment(str(ledger), TERM, category="needs-explanation",
                      explained="no", notes="gap", paths=[str(doc)])

    d = _diff(doc, ledger)
    assert not any(x["term"] == TERM for x in d["new"]), "judged term must not be NEW"
    assert d["matched"] >= 1


def test_moved_clears_after_rejudge(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text(f"# H\n\nThe {TERM} appears first here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), TERM, explained="no", notes="gap", paths=[str(doc)])

    # reword the first-occurrence line -> hash changes -> MOVED
    doc.write_text(f"# H\n\nThe {TERM} shows up in a reworded sentence.\n", encoding="utf-8")
    d = _diff(doc, ledger)
    assert any(x["term"] == TERM for x in d["moved"]), "reworded first line should be MOVED"

    # AI re-judges with paths -> must re-sync first_seen/hash
    e.record_judgment(str(ledger), TERM, explained="yes",
                      notes="reworded but still glossed", paths=[str(doc)])

    d = _diff(doc, ledger)
    assert not any(x["term"] == TERM for x in d["moved"]), \
        "MOVED must clear after re-judge with paths (ISSUE-01)"
    assert d["matched"] >= 1


def test_gone_reported(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text(f"# H\n\nThe {TERM} appears.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), TERM, explained="no", paths=[str(doc)])
    # a term with no paths and no occurrence cannot be created — it must error
    # and leave the ledger untouched (not add an un-locatable ghost row).
    result = e.record_judgment(str(ledger), "GhostTerm", explained="na",
                               category="exclude", notes="not in text", paths=None)
    assert result.startswith("error"), "creating a term without paths must fail"
    _, rows = e.read_ledger(str(ledger))
    assert "GhostTerm" not in e.index(rows), "un-locatable term must not be added"
    # remove the term from the doc
    doc.write_text("# H\n\nnothing here.\n", encoding="utf-8")
    d = _diff(doc, ledger)
    assert TERM in d["gone"]
