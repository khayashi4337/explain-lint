"""
explain-lint MCPサーバー — 決定的論理コアをLLMクライアントに公開する。

機械コア（explain_lintパッケージ）は各用語の初出を見つけ、台帳と差分を取る。
*判断*——この用語は用語解説が必要か？初出で実際に説明されているか？——は
LLMの仕事である。このサーバーはその接点: アシスタントにリンターの駆動を許す。

アシスタントが実行する典型的なループ:
    1. lint_report(paths)                  -> どの用語が NEW / MOVED か
    2. get_term_context(term, paths)       -> 各用語の導入箇所を読む
    3. record_judgment(...)                -> 評定を台帳に書き込む
    4. list_gaps(ledger)                   -> 未説明用語を人間に報告

サーバーはモデルを持たず、API呼び出しも行わない; 決定的論理でオフラインの
ままである。知能は接続するクライアント側にある。

実行:  python explain_lint_mcp.py           (stdioトランスポート)
依存: pip install mcp        (explain_lintコアは何も不要)
"""
import os
from mcp.server.fastmcp import FastMCP

import explain_lint as core

mcp = FastMCP("explain-lint")

# 抽出デフォルトはコアから取得。CLIとMCPで対称に保つ（ISSUE-06）
_MK = core.DEFAULT_MIN_KANA
_ML = core.DEFAULT_MIN_LATIN
_MJ = core.DEFAULT_MIN_KANJI


def _extract_kw(use_kana, use_latin, use_morph, min_kana, min_latin, min_kanji):
    return dict(use_kana=use_kana, use_latin=use_latin, use_morph=use_morph,
                min_kana=min_kana, min_latin=min_latin, min_kanji=min_kanji)


@mcp.tool()
def lint_report(paths: list[str], ledger: str = "", use_kana: bool = True,
                use_latin: bool = True, use_morph: bool = False,
                min_kana: int = _MK, min_latin: int = _ML,
                min_kanji: int = _MJ) -> dict:
    """文章ファイルと台帳を比較し、変更点を報告する。

    これを最初に呼ぶ。判断が必要な用語を返す:
      - new:   台帳にない用語（各々を判断: 用語解説が必要か？初出で説明されているか？）。
               各アイテムは term, first_seen, line_text を持つため、2回目の呼び出しなしで
               判断できることが多い。
      - moved: 初出行が書き換えられた用語——再判断が必要。
      - gone:  台帳にあるがテキストから見つからなくなった用語。
      - matched: 変更のない既判定用語の数（スキップ可）。

    paths: 読み順のMarkdown/テキストファイル。
    ledger: 台帳パス（デフォルト: <最初のパス>.terms.md）。
    use_kana/use_latin/use_morph/min_kana/min_latin/min_kanji: 抽出のチューニング（CLIと同じ）。
    use_morph が True の場合、形態素解析で漢字・ひらがな名詞を抽出する（要: pip install janome）。
    """
    ledger_path = ledger or core.default_ledger(paths)
    first = core.scan(paths, **_extract_kw(use_kana, use_latin, use_morph, min_kana, min_latin, min_kanji))
    _, rows = core.read_ledger(ledger_path)
    d = core.diff(first, core.index(rows))
    trim = lambda o: {"term": o["term"], "first_seen": o["first_seen"],
                      "line_text": o["text"]}
    return {
        "ledger": ledger_path,
        "counts": {"total": len(first), "ledger": len(rows), "matched": d["matched"],
                   "new": len(d["new"]), "moved": len(d["moved"]), "gone": len(d["gone"])},
        "new": [trim(o) for o in d["new"]],
        "moved": [{**trim(o), "was": o["was"]} for o in d["moved"]],
        "gone": d["gone"],
    }


@mcp.tool()
def get_term_context(term: str, paths: list[str], window: int = 2,
                     use_kana: bool = True, use_latin: bool = True,
                     use_morph: bool = False,
                     min_kana: int = _MK, min_latin: int = _ML,
                     min_kanji: int = _MJ) -> dict:
    """指定用語の初出と周辺行を返す。判断材料として使う。

    lint_report の line_text だけでは初出で説明されているか判断できない場合に使う。
    `window` は前後に含める行数。用語が一度も出現しない場合は {found:false} を返す。
    """
    ctx = core.get_context(term, paths, window=window,
                           **_extract_kw(use_kana, use_latin, use_morph, min_kana, min_latin, min_kanji))
    if ctx is None:
        return {"found": False, "term": term}
    return {"found": True, **ctx}


@mcp.tool()
def record_judgment(ledger: str, term: str, category: str = "", explained: str = "",
                    notes: str = "", paths: list[str] | None = None,
                    use_kana: bool = True, use_latin: bool = True,
                    use_morph: bool = False,
                    min_kana: int = _MK, min_latin: int = _ML,
                    min_kanji: int = _MJ) -> dict:
    """用語の評定を台帳に書き込む（行を作成、または更新）。

    category:  needs-explanation | common | proper-noun | exclude
    explained: yes | no | na    (`no` = 用語解説が必要でまだない——発見事項）
    notes:     短い自由テキスト。
    paths:     台帳にない新規用語の行作成に必要。また、MOVED用語の位置を
               更新時に再同期するのにも必要。既存行の評定のみの編集なら省略可。
    use_kana/use_latin/use_morph/min_kana/min_latin/min_kanji: 抽出のチューニング（CLIと同じ）。
    戻り値 {action: created|updated|error, detail}。
    """
    kw = _extract_kw(use_kana, use_latin, use_morph, min_kana, min_latin, min_kanji) if paths else {}
    action = core.record_judgment(ledger, term, category=category or None,
                                  explained=explained or None, notes=notes or None,
                                  paths=paths, **kw)
    ok = action in ("created", "updated")
    return {"action": action if ok else "error", "detail": "" if ok else action,
            "ledger": ledger, "term": term}


@mcp.tool()
def list_gaps(ledger: str) -> dict:
    """`explained = no` と判定された用語を一覧——アクションすべき出力（未解説用語）。"""
    gaps = core.list_gaps(ledger)
    return {"count": len(gaps),
            "gaps": [{"term": r["term"], "first_seen": r["first_seen"],
                      "notes": r["notes"]} for r in gaps]}


@mcp.tool()
def sync_ledger(paths: list[str], ledger: str = "", use_kana: bool = True,
                use_latin: bool = True, use_morph: bool = False,
                min_kana: int = _MK, min_latin: int = _ML,
                min_kanji: int = _MJ) -> dict:
    """行がずれた用語（hash不変）の台帳行番号を書き換える。

    行番号がずれるだけの編集後に実行し、純粋なずれでは lint_report が黙り、
    本当の文脈変更のみをフラグするようにする。
    """
    ledger_path = ledger or core.default_ledger(paths)
    if not os.path.exists(ledger_path):
        return {"updated": 0, "error": f"no ledger at {ledger_path}"}
    updated = core.sync_linenumbers(
        paths, ledger_path, **_extract_kw(use_kana, use_latin, use_morph, min_kana, min_latin, min_kanji))
    return {"updated": updated, "ledger": ledger_path}


@mcp.tool()
def dump_terms(paths: list[str], use_kana: bool = True, use_latin: bool = True,
               use_morph: bool = False,
               min_kana: int = _MK, min_latin: int = _ML,
               min_kanji: int = _MJ) -> dict:
    """全用語の初出を一覧（新規台帳のシード材料）。"""
    first = core.scan(paths, **_extract_kw(use_kana, use_latin, use_morph, min_kana, min_latin, min_kanji))
    items = sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"]))
    return {"count": len(first),
            "terms": [{"term": t, "first_seen": core.fmt_seen(o["file"], o["line"], o["heading"], o.get("page", 0)),
                       "hash": o["hash"]} for t, o in items]}


if __name__ == "__main__":
    mcp.run()
