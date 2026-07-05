"""コマンドラインエントリポイント（`python -m explain_lint` / `explain-lint`）。

表示のみ: 印刷と整形を行う唯一のモジュール。コア（extract / ledger / diff）は
一切出力しないため、インポート可能でテスト可能なまま保たれる。
"""
import argparse
import os
import sys

from .patterns import DEFAULT_MIN_KANA, DEFAULT_MIN_LATIN
from .extract import fmt_seen, scan
from .ledger import default_ledger, index, list_gaps, read_ledger
from .diff import diff, sync_linenumbers

PROG = "explain-lint"

# --- CLIメッセージの国際化（i18n） ---
# --lang で言語を切り替え。デフォルトは en（テストの後方互換性のため）。
_MSGS = {
    "en": {
        "terms_count": "# {n} terms",
        "no_ledger_sync": "no ledger at {path} (seed one with --dump first)",
        "sync_result": "[--sync] updated {n} line-number(s)",
        "gaps_header": "[explain-lint] {n} unexplained term(s) (explained=no):",
        "report_header": "[explain-lint] {terms} terms / ledger {ledger} / matched {matched}",
        "no_ledger_hint": "  (no ledger at {path}; seed one:  python -m explain_lint {input} --dump)",
        "new_header": "  NEW ({n}) — need a judgment:",
        "new_more": "    ... and {n} more",
        "moved_header": "  MOVED ({n}) — first-occurrence context changed, re-judge:",
        "gone_header": "  GONE ({n}) — in ledger, not in text: {terms}",
        "ok": "  OK no new or moved terms",
    },
    "ja": {
        "terms_count": "# {n} 件の用語",
        "no_ledger_sync": "台帳がありません: {path}（先に --dump で作成してください）",
        "sync_result": "[--sync] {n} 件の行番号を更新しました",
        "gaps_header": "[explain-lint] {n} 件の未説明用語 (explained=no):",
        "report_header": "[explain-lint] 用語 {terms} 件 / 台帳 {ledger} 件 / 一致 {matched} 件",
        "no_ledger_hint": "  （台帳がありません: {path}; 作成:  python -m explain_lint {input} --dump）",
        "new_header": "  NEW（{n}件）— 判断が必要:",
        "new_more": "    ... 他 {n} 件",
        "moved_header": "  MOVED（{n}件）— 初出の文脈が変更されました。再判断してください:",
        "gone_header": "  GONE（{n}件）— 台帳にあるが本文から消滅: {terms}",
        "ok": "  OK 新規・移動の用語はありません",
    },
}


def _msg(lang: str, key: str, **kw) -> str:
    """指定言語のメッセージテンプレートをフォーマットして返す。"""
    return _MSGS.get(lang, _MSGS["en"])[key].format(**kw)


def main() -> None:
    # 非UTF-8コンソール（例: Windows cp932）でもクラッシュしないようにする:
    # レポート/dump出力には `—` と `§` が含まれ、そのままでは
    # UnicodeEncodeError が発生する（ISSUE-03）。CLIエントリポイントに限定;
    # コア関数は一切出力しない。
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass  # 既にラップ済みまたは再設定不可のストリーム（例: テストキャプチャ）

    ap = argparse.ArgumentParser(prog=PROG, description="Lint prose for unexplained terms.")
    ap.add_argument("inputs", nargs="+", help="Markdown/text file(s), in reading order")
    ap.add_argument("--ledger", help="ledger file (default: <first-input>.terms.md)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dump", action="store_true", help="print all first occurrences")
    mode.add_argument("--sync", action="store_true", help="update ledger line numbers")
    mode.add_argument("--gaps", action="store_true", help="list terms marked explained=no")
    ap.add_argument("--no-kana", action="store_true")
    ap.add_argument("--no-latin", action="store_true")
    ap.add_argument("--min-kana", type=int, default=DEFAULT_MIN_KANA)
    ap.add_argument("--min-latin", type=int, default=DEFAULT_MIN_LATIN)
    ap.add_argument("--lang", default="en", choices=["en", "ja"],
                    help="CLI output language (default: en)")
    args = ap.parse_args()
    L = args.lang

    ledger_path = args.ledger or default_ledger(args.inputs)
    kw = dict(use_kana=not args.no_kana, use_latin=not args.no_latin,
              min_kana=args.min_kana, min_latin=args.min_latin)

    if args.dump:
        first = scan(args.inputs, **kw)
        print("term\tfirst_seen\thash\tline")
        for t, o in sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"])):
            print(f"{t}\t{fmt_seen(o['file'], o['line'], o['heading'])}\t{o['hash']}\t{o['text'][:100]}")
        print(f"\n" + _msg(L, "terms_count", n=len(first)), file=sys.stderr)
        return

    if args.sync:
        if not os.path.exists(ledger_path):
            sys.exit(_msg(L, "no_ledger_sync", path=ledger_path))
        print(_msg(L, "sync_result", n=sync_linenumbers(args.inputs, ledger_path, **kw)))
        return

    if args.gaps:
        gaps = list_gaps(ledger_path)
        print(_msg(L, "gaps_header", n=len(gaps)))
        for r in gaps:
            print(f"    {r['first_seen']}: {r['term']}  {('— ' + r['notes']) if r['notes'] else ''}")
        return

    first = scan(args.inputs, **kw)
    _, rows = read_ledger(ledger_path)
    d = diff(first, index(rows))
    print(_msg(L, "report_header", terms=len(first), ledger=len(rows), matched=d['matched']))
    if not rows:
        print(_msg(L, "no_ledger_hint", path=ledger_path, input=args.inputs[0]))
    if d["new"]:
        print(_msg(L, "new_header", n=len(d['new'])))
        for r in d["new"][:60]:
            print(f"    {r['first_seen']}: {r['term']}")
        if len(d["new"]) > 60:
            print(_msg(L, "new_more", n=len(d['new']) - 60))
    if d["moved"]:
        print(_msg(L, "moved_header", n=len(d['moved'])))
        for r in d["moved"][:40]:
            print(f"    {r['term']}: {r['was']} -> {r['first_seen']}")
    if d["gone"]:
        print(_msg(L, "gone_header", n=len(d['gone']), terms=', '.join(d['gone'][:15])))
    if not (d["new"] or d["moved"]):
        print(_msg(L, "ok"))
    if d["new"] or d["moved"]:
        sys.exit(1)
