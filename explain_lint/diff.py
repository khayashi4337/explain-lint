"""差分: スキャン結果と台帳を比較し、純粋な行ずれを同期する。"""
from typing import TypedDict

from .extract import fmt_seen, scan
from .ledger import read_ledger, write_ledger


class DiffResult(TypedDict):
    new: list
    moved: list
    gone: list
    matched: int


def diff(first, ledger_idx) -> DiffResult:
    """スキャン結果(first) と台帳インデックスを比較し、{new, moved, gone, matched} を返す。

    new:   台帳にない用語（判断が必要）
    moved: 初出行のテキストが変更された（hash不一致）→再判断
    gone:  台帳にあるがテキストから消えた用語
    matched: 変更のない既判定用語の数
    """
    new, moved, matched = [], [], 0
    for t, occ in sorted(first.items(), key=lambda kv: (kv[1]["file"], kv[1]["line"])):
        e = ledger_idx.get(t)
        seen = fmt_seen(occ["file"], occ["line"], occ["heading"])
        if e is None:
            new.append({"term": t, "first_seen": seen, **occ})
        elif e["hash"] != occ["hash"]:
            moved.append({"term": t, "first_seen": seen, "was": e["first_seen"], **occ})
        else:
            matched += 1
    gone = [t for t in ledger_idx if t not in first]
    return {"new": new, "moved": moved, "gone": gone, "matched": matched}


def sync_linenumbers(paths, ledger_path: str, **scan_kw) -> int:
    """hash一致する用語の行番号を書き換える。更新数を返す。

    純粋な行ずれ（hash一致）のみ同期する。内容変更（hash不一致）は
    MOVED として record_judgment に委ね、黙って書き換えない。
    """
    preamble, rows = read_ledger(ledger_path)
    first = scan(paths, **scan_kw)
    updated = 0
    for r in rows:
        occ = first.get(r["term"])
        if occ and occ["hash"] == r["hash"]:
            seen = fmt_seen(occ["file"], occ["line"], occ["heading"])
            if seen != r["first_seen"]:
                r["first_seen"] = seen
                updated += 1
    if updated:
        write_ledger(ledger_path, preamble, rows)
    return updated
