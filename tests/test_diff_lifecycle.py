"""ISSUE-01回帰テスト: 用語の差分状態が正しく遷移することを確認する。

NEW -> record_judgment -> matched（NEWではなくなる）
初出の書き換え -> MOVED -> record_judgment(paths) -> matched（MOVEDがクリアされる）

MOVEDクリアのケースは修正前のコードで失敗する: record_judgmentの更新分岐が
first_seen/hashを再同期していなかったため、再判断されたMOVED用語が永遠に
MOVEDのままだった。
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
    assert any(x["term"] == TERM for x in d["new"]), "NEWとして開始されるべき"

    e.record_judgment(str(ledger), TERM, category="needs-explanation",
                      explained="no", notes="gap", paths=[str(doc)])

    d = _diff(doc, ledger)
    assert not any(x["term"] == TERM for x in d["new"]), "判断済みの用語はNEWであってはならない"
    assert d["matched"] >= 1


def test_moved_clears_after_rejudge(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text(f"# H\n\nThe {TERM} appears first here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), TERM, explained="no", notes="gap", paths=[str(doc)])

    # 初出行を書き換え -> hashが変化 -> MOVED
    doc.write_text(f"# H\n\nThe {TERM} shows up in a reworded sentence.\n", encoding="utf-8")
    d = _diff(doc, ledger)
    assert any(x["term"] == TERM for x in d["moved"]), "書き換えられた初出行はMOVEDであるべき"

    # AIがpaths付きで再判断 -> first_seen/hashを再同期する必要がある
    e.record_judgment(str(ledger), TERM, explained="yes",
                      notes="reworded but still glossed", paths=[str(doc)])

    d = _diff(doc, ledger)
    assert not any(x["term"] == TERM for x in d["moved"]), \
        "MOVEDはpaths付き再判断後にクリアされる必要がある（ISSUE-01）"
    assert d["matched"] >= 1


def test_gone_reported(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text(f"# H\n\nThe {TERM} appears.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), TERM, explained="no", paths=[str(doc)])
    # pathsがなく出現もしない用語は作成できない——エラーになり、
    # 台帳は変更されない（位置特定不可能なゴースト行が追加されない）。
    result = e.record_judgment(str(ledger), "GhostTerm", explained="na",
                               category="exclude", notes="not in text", paths=None)
    assert result.startswith("error"), "pathsなしの用語作成は失敗する必要がある"
    _, rows = e.read_ledger(str(ledger))
    assert "GhostTerm" not in e.index(rows), "位置特定不可能な用語は追加されてはならない"
    # 用語をドキュメントから削除
    doc.write_text("# H\n\nnothing here.\n", encoding="utf-8")
    d = _diff(doc, ledger)
    assert TERM in d["gone"]
