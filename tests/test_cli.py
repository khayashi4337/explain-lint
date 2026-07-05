"""ISSUE-03回帰テスト: 非UTF-8コンソールでCLIがクラッシュしないことを確認する。

レポート/dump出力には `—`（emダッシュ）と `§` が含まれる。cp932/asciiコンソールでは
UnicodeEncodeErrorが発生し、デフォルトでツールが異常終了する——開発中は毎回
PYTHONIOENCODING=utf-8を手動設定していたため隠れていた。CLIは自身のストリームを
再設定し、コンソールエンコーディングに関わらず生き残る必要がある。

また --lang ja で日本語メッセージが正しく出力されることを確認する（i18nテスト）。
"""
import os
import subprocess
import sys

import explain_lint as e

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(args, extra_env=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "ascii"  # § や — をエンコードできないコンソール
    if extra_env:
        env.update(extra_env)
    return subprocess.run([sys.executable, "-m", "explain_lint", *args],
                          cwd=REPO, capture_output=True, env=env)


def _clean(r):
    err = r.stderr.decode("utf-8", "replace")
    assert "UnicodeEncodeError" not in err, err
    assert "Traceback" not in err, err
    return r.stdout.decode("utf-8", "replace")


def test_report_survives_ascii_console(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    r = _run([str(doc), "--ledger", str(tmp_path / "l.md")])
    out = _clean(r)
    assert r.returncode in (0, 1)
    assert "NEW" in out  # レポートが実際にNEWセクションを出力した


def test_dump_survives_ascii_console(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    r = _run([str(doc), "--dump"])
    _clean(r)
    assert r.returncode == 0


def test_gaps_survives_ascii_console(tmp_path):
    # gaps出力には §（first_seen）と —（notes区切り）の両方が含まれる。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), "オブザーバブル", category="needs-explanation",
                      explained="no", notes="gap", paths=[str(doc)])
    r = _run([str(doc), "--gaps", "--ledger", str(ledger)])
    out = _clean(r)
    assert r.returncode == 0
    assert "オブザーバブル" in out


def test_lang_ja_output(tmp_path):
    # --lang ja で日本語メッセージが出力されることを確認する。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    r = _run([str(doc), "--ledger", str(tmp_path / "l.md"), "--lang", "ja"])
    out = _clean(r)
    assert r.returncode in (0, 1)
    assert "用語" in out  # 日本語メッセージが含まれる
    assert "件" in out   # 日本語メッセージが含まれる


def test_lang_en_default(tmp_path):
    # デフォルト（--lang なし）は英語メッセージ。
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    r = _run([str(doc), "--ledger", str(tmp_path / "l.md")])
    out = _clean(r)
    assert r.returncode in (0, 1)
    assert "terms" in out  # 英語メッセージ
    assert "件" not in out  # 日本語メッセージは含まれない


# --- ISSUE-12: ファイル不在時のエラーハンドリング ---

def test_file_not_found_error(tmp_path):
    # 存在しないファイルを指定した場合、トレースバックではなくエラーメッセージ。
    r = _run([str(tmp_path / "nonexistent.md"), "--dump"])
    err = r.stderr.decode("utf-8", "replace")
    assert r.returncode != 0
    assert "file not found" in err
    assert "Traceback" not in err


def test_file_not_found_error_pdf(tmp_path):
    # 存在しないPDFファイルを指定した場合もエラーメッセージ。
    r = _run([str(tmp_path / "nonexistent.pdf"), "--dump"])
    err = r.stderr.decode("utf-8", "replace")
    assert r.returncode != 0
    assert "file not found" in err
    assert "Traceback" not in err


def test_file_not_found_error_default_mode(tmp_path):
    # デフォルトモードでもファイル不在時にエラーメッセージ。
    r = _run([str(tmp_path / "nonexistent.md"), "--ledger", str(tmp_path / "l.md")])
    err = r.stderr.decode("utf-8", "replace")
    assert r.returncode != 0
    assert "file not found" in err
    assert "Traceback" not in err
