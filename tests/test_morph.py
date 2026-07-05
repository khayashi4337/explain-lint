"""ISSUE-09: 形態素解析による漢字・ひらがな用語抽出。

use_morph=True の場合、漢字・ひらがなを含む名詞（例: 量子力学、固有値）が
抽出される。Janomeが未インストールの場合は正規表現フォールバックに切り替わる。
既存のカタカナ抽出・ラテン文字抽出は回帰しない。
"""
import explain_lint as e


def _terms(tmp_path, text, **kw):
    doc = tmp_path / "d.md"
    doc.write_text(text, encoding="utf-8")
    return set(e.scan([str(doc)], **kw).keys())


def test_morph_extracts_kanji_terms(tmp_path):
    # --morph で漢字混在の専門用語が抽出される。
    t = _terms(tmp_path, "量子力学と固有値について議論する。\n", use_morph=True)
    assert "量子力学" in t or "量子" in t  # Janomeなら分割される可能性
    assert "固有値" in t


def test_morph_extracts_hiragana_kanji_mixed(tmp_path):
    # 漢字+ひらがなの複合語も抽出される。
    t = _terms(tmp_path, "非線形効果が観測された。\n", use_morph=True)
    assert "非線形効果" in t or "非線形" in t


def test_morph_stopwords_filtered(tmp_path):
    # ストップワード（もの、こと等）は抽出されない。
    t = _terms(tmp_path, "このことについて話す。\n", use_morph=True)
    assert "こと" not in t
    assert "もの" not in t


def test_morph_katakana_not_duplicated(tmp_path):
    # カタカナ用語は KATAKANA 正規表現で抽出されるため、形態素解析で重複しない。
    t = _terms(tmp_path, "オブザーバブルと量子力学\n", use_morph=True)
    assert "オブザーバブル" in t  # KATAKANA正規表現から
    assert "量子力学" in t or "量子" in t  # 形態素解析から


def test_morph_min_kanji_param(tmp_path):
    # min_kanji で最小文字数を制御できる。
    txt = "力学と量子力学\n"
    t_short = _terms(tmp_path, txt, use_morph=True, min_kanji=3)
    t_long = _terms(tmp_path, txt, use_morph=True, min_kanji=5)
    # min_kanji=3 では "力学"(2文字)は弾かれるが "量子力学"(4文字)は通る
    assert "量子力学" in t_short
    # min_kanji=5 では "量子力学"(4文字)も弾かれる
    assert "量子力学" not in t_long


def test_no_morph_default_does_not_extract_kanji(tmp_path):
    # デフォルト（use_morph=False）では漢字用語は抽出されない。
    t = _terms(tmp_path, "量子力学と固有値\n")
    assert "量子力学" not in t
    assert "固有値" not in t


def test_morph_does_not_break_kana_latin(tmp_path):
    # --morph 有効時もカタカナ・ラテン文字抽出は正常動作する。
    t = _terms(tmp_path, "オブザーバブル and Fourier and 量子力学\n", use_morph=True)
    assert "オブザーバブル" in t
    assert "Fourier" in t
    assert "量子力学" in t or "量子" in t
