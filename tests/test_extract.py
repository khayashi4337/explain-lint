"""ISSUE-04: 抽出ポリシー——略語、最小文字数パラメータ、除外。

旧LATIN正規表現は英語の大文字3文字以上をハードコードしており、
`AT&T` / `R&D` を捕捉できなかった（固有名詞トラッカーが構造的に
正規の固有名詞を見逃していた）。最小長が正規表現（Latin）と
パラメータ（kana）に分割されていた。これを統合し略語漏れを修正する。
"""
import explain_lint as e


def _terms(tmp_path, text, **kw):
    doc = tmp_path / "d.md"
    doc.write_text(text, encoding="utf-8")
    return set(e.scan([str(doc)], **kw).keys())


def test_abbreviations_captured(tmp_path):
    t = _terms(tmp_path, "AT&T and R&D and Peacock-Hall and Runge-Kutta appear.\n")
    assert "AT&T" in t
    assert "R&D" in t
    assert "Peacock-Hall" in t
    assert "Runge-Kutta" in t


def test_single_and_short_capitals_filtered(tmp_path):
    # min_latin=3（デフォルト）: 単発の大文字と2文字単語はノイズ。
    t = _terms(tmp_path, "I think A cat and Dr Smith wrote Nice things.\n")
    assert "I" not in t and "A" not in t and "Dr" not in t
    assert "Nice" in t and "Smith" in t


def test_min_latin_param(tmp_path):
    assert "Go" not in _terms(tmp_path, "Go Foo now.\n", min_latin=3)
    assert "Go" in _terms(tmp_path, "Go Foo now.\n", min_latin=2)
    assert "Foo" in _terms(tmp_path, "Go Foo now.\n", min_latin=3)


def test_min_kana_param(tmp_path):
    txt = "コア オブザーバブル\n"  # コア=2文字, オブザーバブル=7文字
    assert "コア" not in _terms(tmp_path, txt, min_kana=3)
    assert "コア" in _terms(tmp_path, txt, min_kana=2)
    assert "オブザーバブル" in _terms(tmp_path, txt, min_kana=3)


def test_cap_lowercase_hyphen_not_overcaptured(tmp_path):
    # "Foo-bar"（大文字+小文字）は結合された固有名詞ではない; "Foo"を捕捉。
    t = _terms(tmp_path, "The Foo-bar thing.\n")
    assert "Foo" in t
    assert "Foo-bar" not in t


def test_lowercase_start_still_excluded(tmp_path):
    # 大文字始まりのみがデフォルト; 小文字の専門用語は捕捉対象外。
    t = _terms(tmp_path, "a qubit and an eigenvalue.\n")
    assert "qubit" not in t and "eigenvalue" not in t


def test_exclusions_still_hold(tmp_path):
    # コードフェンス / インラインコード / $数式$ / URL は引き続き除外される必要がある。
    txt = (
        "# H\n\n"
        "Real Term here.\n"
        "`InlineCode` and $MathSym$ and https://Example.com/Path\n"
        "```\nFencedTerm\n```\n"
    )
    t = _terms(tmp_path, txt)
    assert "Term" in t
    assert "InlineCode" not in t
    assert "MathSym" not in t
    assert "FencedTerm" not in t
