"""ISSUE-07: a table row in the preamble must not be read as a ledger data row.

read_ledger identified data rows by "6 cells and an 8-hex 4th column". A stray
Markdown table row in the preamble (docs, an example) that happened to match
was mis-parsed as data. The table region is now bounded by the header + `|---|`
separator, so only rows after the separator count.
"""
import explain_lint as e


def test_preamble_table_row_not_parsed_as_data(tmp_path):
    ledger = tmp_path / "l.terms.md"
    preamble = (
        "# my ledger\n\n"
        "For example, a row looks like:\n\n"
        "| word | needs-explanation | doc.md:5 | deadbeef | no | note |\n\n"
    )
    rows = [{"term": "Real", "category": "needs-explanation",
             "first_seen": "d.md:5 §H", "hash": "abcdef12",
             "explained": "no", "notes": ""}]
    e.write_ledger(str(ledger), preamble, rows)
    _, back = e.read_ledger(str(ledger))
    assert len(back) == 1, "only the one real data row should be parsed"
    idx = e.index(back)
    assert "Real" in idx
    assert "word" not in idx  # the preamble's illustrative row is not data


def test_preamble_full_skeleton_stable_roundtrip(tmp_path):
    # a preamble that quotes a FULL fake table (header + separator + a
    # data-shaped row) must not leak the fake row and must not accumulate
    # duplicates across repeated read/write cycles (ISSUE-07, robust anchor).
    ledger = tmp_path / "l.terms.md"
    preamble = (
        "# ledger\n\nFor example, the table looks like:\n\n"
        "| term | category | first_seen | hash | explained | notes |\n"
        "|---|---|---|---|---|---|\n"
        "| word | c | d.md:1 | deadbeef | no | x |\n\n"
    )
    rows = [{"term": "Real", "category": "c", "first_seen": "d.md:5 §H",
             "hash": "abcdef12", "explained": "no", "notes": ""}]
    e.write_ledger(str(ledger), preamble, rows)
    for _ in range(2):
        pre, back = e.read_ledger(str(ledger))
        assert [r["term"] for r in back] == ["Real"], "fake skeleton row must not leak"
        e.write_ledger(str(ledger), pre, back)
    _, final = e.read_ledger(str(ledger))
    assert [r["term"] for r in final] == ["Real"]  # stable, no duplication


def test_normal_ledger_still_reads(tmp_path):
    # the header + separator + rows path must still work unchanged.
    ledger = tmp_path / "l.terms.md"
    rows = [
        {"term": "Foo", "category": "c", "first_seen": "d.md:1 §A",
         "hash": "11111111", "explained": "no", "notes": ""},
        {"term": "Bar", "category": "c", "first_seen": "d.md:2 §B",
         "hash": "22222222", "explained": "na", "notes": ""},
    ]
    e.write_ledger(str(ledger), e.DEFAULT_PREAMBLE, rows)
    _, back = e.read_ledger(str(ledger))
    assert [r["term"] for r in back] == ["Foo", "Bar"]
