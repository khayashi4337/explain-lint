"""ISSUE-17: 角括弧の構造ラベル・IDが偽の用語として抽出される問題。

論文（「観測の窓」v2）の閉包分類ラベル `[PREM]`/`[CLOS]` や名前付きID
`[LEM:S4-FIVEELEVEN]` が LATIN 抽出に引っかかり、構造マーカーが大量に
偽用語として台帳を汚染していた。全大文字で始まる角括弧トークンを
汎用的に除外する（特定プレフィックスをハードコードしない）。
"""
import explain_lint as e


def _terms(tmp_path, text, **kw):
    doc = tmp_path / "d.md"
    doc.write_text(text, encoding="utf-8")
    return set(e.scan([str(doc)], **kw).keys())


def test_bare_bracket_labels_excluded(tmp_path):
    t = _terms(tmp_path, "この主張は [PREM] であり [CLOS] として閉じる。[CORE] も参照。\n")
    assert "PREM" not in t
    assert "CLOS" not in t
    assert "CORE" not in t


def test_named_bracket_ids_excluded(tmp_path):
    t = _terms(tmp_path, (
        "詳細は [LEM:S4-FIVEELEVEN] と [THM:STEINWEISS] と "
        "[FACT:S5-IRREP7] と [OBS:WINDOW-M-OPEN] を見よ。\n"
    ))
    assert not {"S4", "FIVEELEVEN", "STEINWEISS", "S5", "IRREP7", "WINDOW", "OPEN"} & t
    assert "LEM" not in t and "THM" not in t and "FACT" not in t and "OBS" not in t


def test_prefix_not_hardcoded(tmp_path):
    # DEF/LEM/THM/OBS/FACT に限らず、任意の全大文字プレフィックスが除外される。
    t = _terms(tmp_path, "未知のラベル [XVER] と [HYPO] と [OGEO] が使われる。\n")
    assert not {"XVER", "HYPO", "OGEO"} & t


def test_normal_capitalized_words_still_captured(tmp_path):
    # 角括弧を使わない通常の大文字語（略語含む）は従来通り抽出される（ISSUE-04の回帰なし）。
    t = _terms(tmp_path, "AT&T and NASA and Peacock-Hall appear without brackets.\n")
    assert "AT&T" in t
    assert "NASA" in t
    assert "Peacock-Hall" in t


def test_link_text_still_captured(tmp_path):
    # 通常のMarkdownリンク[Some Term](url)は大文字だけの語にならないため誤爆しない。
    t = _terms(tmp_path, "See [Some Term](https://example.com/path) for details.\n")
    assert "Some" in t and "Term" in t


def test_lowercase_bracket_content_not_stripped(tmp_path):
    # 小文字を含む角括弧は構造ラベルではないため、除外対象外(中身は素通り)。
    t = _terms(tmp_path, "参照 [see Appendix] にて Detail を扱う。\n")
    assert "Appendix" in t
    assert "Detail" in t
