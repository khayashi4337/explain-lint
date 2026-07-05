"""ISSUE-08: PDF入力対応 + 索引（back-of-book index）生成。

PDFファイルを入力として用語検出ができること。
台帳にページ番号が記録されること（first_seen が file:pN 形式）。
--index で索引形式の出力が得られること。
既存のMarkdown入力に対する動作が回帰しないこと。
"""
import os
import subprocess
import sys

import explain_lint as e

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _has_pypdf():
    try:
        import pypdf
        return True
    except ImportError:
        return False


def test_index_from_ledger(tmp_path):
    # --index で台帳から索引が生成される。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), "オブザーバブル", category="needs-explanation",
                      explained="no", notes="gap", paths=[str(doc)])
    entries = e.generate_index(str(ledger))
    assert len(entries) == 1
    assert entries[0][0] == "オブザーバブル"
    assert "d.md" in entries[0][1]


def test_index_sorted(tmp_path):
    # 索引は用語でソートされている。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nオブザーバブル and コヒーレンス and フーリエ\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    for term in ["オブザーバブル", "コヒーレンス", "フーリエ"]:
        e.record_judgment(str(ledger), term, explained="no", paths=[str(doc)])
    entries = e.generate_index(str(ledger))
    terms = [t for t, _ in entries]
    assert terms == sorted(terms)


def test_index_empty_ledger(tmp_path):
    # 台帳がない場合は空リスト。
    entries = e.generate_index(str(tmp_path / "nonexistent.md"))
    assert entries == []


def test_index_cli(tmp_path):
    # CLI --index で索引が出力される。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), "オブザーバブル", category="needs-explanation",
                      explained="no", notes="gap", paths=[str(doc)])
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "-m", "explain_lint", str(doc),
                        "--index", "--ledger", str(ledger)],
                       cwd=REPO, capture_output=True, env=env)
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0
    assert "Index" in out
    assert "オブザーバブル" in out


def test_index_cli_no_ledger(tmp_path):
    # 台帳がない場合はエラーメッセージ。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\ntext\n", encoding="utf-8")
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "-m", "explain_lint", str(doc),
                        "--index", "--ledger", str(tmp_path / "nonexistent.md")],
                       cwd=REPO, capture_output=True, env=env)
    assert r.returncode != 0
    err = r.stderr.decode("utf-8", "replace")
    assert "no ledger" in err


def test_pdf_input_without_pypdf(tmp_path, monkeypatch):
    # pypdfが未インストールの場合、PDF入力は空結果を返す（クラッシュしない）。
    # sys.modulesでpypdfをブロックして実際の分岐をテストする。
    import builtins
    real_import = builtins.__import__

    def _block_pypdf(name, *args, **kwargs):
        if name == "pypdf":
            raise ImportError("No module named 'pypdf'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _block_pypdf)
    # キャッシュされたpypdfがあればクリア
    import sys as _sys
    monkeypatch.delitem(_sys.modules, "pypdf", raising=False)

    import explain_lint.extract as ext
    # 存在しないPDFパスでもpypdf未インストール時は空リストを返す
    result = ext._read_lines("nonexistent.pdf")
    assert result == []


def test_markdown_still_works_after_pdf_support(tmp_path):
    # PDF対応の追加でMarkdown入力が回帰しないこと。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    terms = e.scan([str(doc)])
    assert "オブザーバブル" in terms
    assert terms["オブザーバブル"]["line"] == 3


# --- ISSUE-11: PDFサンプルのテスト ---

_PDF_SAMPLE = os.path.join(REPO, "examples", "sample.pdf")
_PDF_SAMPLE_JA = os.path.join(REPO, "examples", "sample_ja.pdf")


def test_pdf_sample_exists():
    # PDFサンプルファイルが存在する。
    assert os.path.exists(_PDF_SAMPLE), "examples/sample.pdf が存在しません"
    assert os.path.exists(_PDF_SAMPLE_JA), "examples/sample_ja.pdf が存在しません"


def test_pdf_sample_extract_terms():
    # PDFサンプルから用語が抽出できること。
    if not _has_pypdf():
        return  # pypdf未インストール時はスキップ
    terms = e.scan([_PDF_SAMPLE])
    assert len(terms) > 0
    assert "Markov" in terms or "Lindblad" in terms
    # PDFの用語はページ番号を行番号として持つ（1ページ目なので line=1）
    for occ in terms.values():
        assert occ["file"] == "sample.pdf"
        assert occ["line"] >= 1
        break


def test_pdf_sample_index():
    # PDFサンプルの台帳から索引が生成できること。
    if not _has_pypdf():
        return
    ledger = _PDF_SAMPLE + ".terms.md"
    if not os.path.exists(ledger):
        return  # 台帳がない場合はスキップ
    entries = e.generate_index(ledger)
    assert len(entries) > 0
