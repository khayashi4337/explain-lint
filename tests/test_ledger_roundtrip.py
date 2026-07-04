"""ISSUE-02 regression: the ledger must survive cells containing '|'.

write_ledger escaped '|' -> '\\|', but read_ledger split on '[^|]', so an
escaped pipe broke column parsing and the whole row VANISHED — a silent data
loss that then re-flagged the term as NEW forever. write/read must be a
symmetric round-trip.
"""
import explain_lint as e


def test_roundtrip_plain(tmp_path):
    ledger = tmp_path / "l.terms.md"
    rows = [
        {"term": "Foo", "category": "needs-explanation", "first_seen": "d.md:5 §Head",
         "hash": "abcdef12", "explained": "no", "notes": "plain note"},
        {"term": "Bar", "category": "exclude", "first_seen": "d.md:9 §Other",
         "hash": "12345678", "explained": "na", "notes": ""},
    ]
    e.write_ledger(str(ledger), e.DEFAULT_PREAMBLE, rows)
    _, back = e.read_ledger(str(ledger))
    assert len(back) == 2
    assert e.index(back)["Foo"]["hash"] == "abcdef12"


def test_roundtrip_with_pipe_in_cells(tmp_path):
    ledger = tmp_path / "l.terms.md"
    rows = [
        {"term": "Foo", "category": "needs-explanation",
         "first_seen": "d.md:5 §Head | with pipe", "hash": "abcdef12",
         "explained": "no", "notes": "note with | pipe"},
        {"term": "Bar", "category": "exclude", "first_seen": "d.md:9 §Plain",
         "hash": "12345678", "explained": "na", "notes": ""},
    ]
    e.write_ledger(str(ledger), e.DEFAULT_PREAMBLE, rows)
    _, back = e.read_ledger(str(ledger))
    assert len(back) == 2, "both rows must survive when a cell contains '|'"
    bi = e.index(back)
    assert bi["Foo"]["first_seen"] == "d.md:5 §Head | with pipe"
    assert bi["Foo"]["notes"] == "note with | pipe"
    assert bi["Bar"]["hash"] == "12345678"


def test_roundtrip_edge_chars(tmp_path):
    """Lone backslash and a doubled '||' must also survive the round-trip."""
    ledger = tmp_path / "l.terms.md"
    rows = [
        {"term": "Back", "category": "c", "first_seen": r"d.md:1 §a\b",
         "hash": "aaaaaaaa", "explained": "no", "notes": r"lone \ backslash"},
        {"term": "Double", "category": "c", "first_seen": "d.md:2 §x || y",
         "hash": "bbbbbbbb", "explained": "no", "notes": "has || double pipe"},
    ]
    e.write_ledger(str(ledger), e.DEFAULT_PREAMBLE, rows)
    _, back = e.read_ledger(str(ledger))
    assert len(back) == 2
    bi = e.index(back)
    assert bi["Back"]["notes"] == r"lone \ backslash"
    assert bi["Double"]["first_seen"] == "d.md:2 §x || y"
    assert bi["Double"]["notes"] == "has || double pipe"


def test_record_judgment_pipe_heading_does_not_vanish(tmp_path):
    """The real-world trigger: a heading with '|' must not delete the row."""
    doc = tmp_path / "d.md"
    doc.write_text("# Head | with pipe\n\nThe オブザーバブル here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), "オブザーバブル", explained="no", notes="x", paths=[str(doc)])
    _, rows = e.read_ledger(str(ledger))
    assert "オブザーバブル" in e.index(rows), "row must survive a pipe in the heading"
    d = e.diff(e.scan([str(doc)]), e.index(rows))
    assert not any(x["term"] == "オブザーバブル" for x in d["new"]), \
        "judged term must not be re-flagged NEW (no silent loss)"
