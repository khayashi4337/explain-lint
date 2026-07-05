"""ISSUE-07: preamble内の表行が台帳データ行として読み取られないことを確認する。

read_ledgerは「6セルかつ第4列が8桁hex」の行をデータ行とみなしていた。preambleに
紛れ込んだMarkdown表行（ドキュメントや例）が偶然この形に一致するとデータとして
誤解析されていた。表領域は header + `|---|` 区切り行で境界化され、区切り行以降の
行のみがデータとして扱われるようになった。
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
    assert len(back) == 1, "実際のデータ行のみが解析されるべき"
    idx = e.index(back)
    assert "Real" in idx
    assert "word" not in idx  # preambleの例示行はデータではない


def test_preamble_full_skeleton_stable_roundtrip(tmp_path):
    # preambleに完全な偽テーブル（header + separator + データ形の行）を引用しても、
    # 偽行が漏れず、繰り返し読み書きしても重複しないことを確認（ISSUE-07, 堅牢アンカー）。
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
        assert [r["term"] for r in back] == ["Real"], "偽の骨組み行は漏れてはならない"
        e.write_ledger(str(ledger), pre, back)
    _, final = e.read_ledger(str(ledger))
    assert [r["term"] for r in final] == ["Real"]  # 安定、重複なし


def test_normal_ledger_still_reads(tmp_path):
    # header + separator + rows のパスが変更なく機能することを確認。
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
