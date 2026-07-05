"""ISSUE-05: sync_linenumbers の挙動。

純粋な行ずれ（同じ行テキスト、新しい行番号）はノイズ: syncは番号を書き換え、
静かに保つ。本当の内容変更（hash不一致）はMOVEDであり、サイレントに同期されては
ならない——再判断が必要（ISSUE-01）。
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

    # 前に空行を追加: 用語の行は移動するがテキスト（hash）は同一
    doc.write_text(f"\n\n\n# H\n\nThe {TERM} here.\n", encoding="utf-8")
    n = e.sync_linenumbers([str(doc)], str(ledger))

    assert n == 1
    _, rows = e.read_ledger(str(ledger))
    new_seen = e.index(rows)[TERM]["first_seen"]
    assert new_seen != old_seen
    assert new_seen.startswith("d.md:6")  # 3行下にずれた


def test_sync_ignores_content_change(tmp_path):
    doc, ledger = _seed(tmp_path, f"# H\n\nThe {TERM} here.\n")
    _, rows = e.read_ledger(str(ledger))
    old_hash = e.index(rows)[TERM]["hash"]
    old_seen = e.index(rows)[TERM]["first_seen"]

    # 行を移動（前に追加）しつつ書き換え。行は移動しているため、単純なsyncは
    # first_seenを書き換えるだろう——しかしhashが変化しているため、hashガードは
    # これをスキップする必要がある。行を移動させることが、n==0を本当の回帰テストに
    # する（同じ行での書き換えなら間違った理由でn==0になる）。
    doc.write_text(f"\n\n\n# H\n\nThe {TERM} now reworded.\n", encoding="utf-8")
    n = e.sync_linenumbers([str(doc)], str(ledger))

    assert n == 0, "内容変更は行が移動していてもサイレントに同期されてはならない"
    _, rows = e.read_ledger(str(ledger))
    assert e.index(rows)[TERM]["hash"] == old_hash  # record_judgmentに委ねる
    assert e.index(rows)[TERM]["first_seen"] == old_seen  # 書き換えられていない
    # そしてMOVEDとして再判断対象に浮上するべき
    d = e.diff(e.scan([str(doc)]), e.index(rows))
    assert any(x["term"] == TERM for x in d["moved"])


def test_sync_noop_when_nothing_moved(tmp_path):
    doc, ledger = _seed(tmp_path, f"# H\n\nThe {TERM} here.\n")
    assert e.sync_linenumbers([str(doc)], str(ledger)) == 0
