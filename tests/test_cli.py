"""ISSUE-03 regression: the CLI must not crash on a non-UTF-8 console.

The report/dump output contains `—` (em-dash) and `§`. On a cp932/ascii console
these raise UnicodeEncodeError and the tool dies out-of-box — masked during
development because every manual run set PYTHONIOENCODING=utf-8. The CLI must
reconfigure its own streams so it survives regardless of the console encoding.
"""
import os
import subprocess
import sys

import explain_lint as e

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(args, extra_env=None):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "ascii"  # a console that cannot encode § or —
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
    assert "NEW" in out  # the report actually printed its NEW section


def test_dump_survives_ascii_console(tmp_path):
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    r = _run([str(doc), "--dump"])
    _clean(r)
    assert r.returncode == 0


def test_gaps_survives_ascii_console(tmp_path):
    # gaps output has both § (first_seen) and — (notes separator).
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), "オブザーバブル", category="needs-explanation",
                      explained="no", notes="gap", paths=[str(doc)])
    r = _run([str(doc), "--gaps", "--ledger", str(ledger)])
    out = _clean(r)
    assert r.returncode == 0
    assert "オブザーバブル" in out
