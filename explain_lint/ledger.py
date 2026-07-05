"""台帳の読み書き、インデックス化、および評定のupsert。

台帳はLLMや人間が編集するMarkdownテーブル。このモジュールはテキストに対して
台帳を正直に保ち、評定の唯一の書き込み手である。
"""
import os
from typing import Optional

from .patterns import COLS, DEFAULT_PREAMBLE, HASH_RE, PIPE_SPLIT, TERMS_SUFFIX
from .extract import fmt_seen, scan


def default_ledger(paths) -> str:
    """入力群のデフォルト台帳パス: <最初の入力> + TERMS_SUFFIX。

    この命名規則の唯一の定義。CLIとMCPサーバーの両方がこれを呼び出すため、
    接尾辞が二重にハードコードされることはない（ISSUE-06）。
    """
    return paths[0] + TERMS_SUFFIX


def _split_row(line: str) -> Optional[list]:
    """Markdownテーブル行をエスケープ解除済みのセル値に分割。行でなければ None。

    エスケープされていない `|` で分割し（セル内の `\\|` は保持）、
    その後 `\\|` -> `|` に復元。これは write_ledger のエスケープの読み取り側——
    両者は常に対称でなければならない（ISSUE-02: エスケープされたパイプが
    解析を壊し行全体が消失していた）。
    """
    line = line.rstrip()
    if not (line.startswith("|") and line.endswith("|")):
        return None
    parts = PIPE_SPLIT.split(line)[1:-1]
    return [p.strip().replace(r"\|", "|") for p in parts]


def _is_separator(cells) -> bool:
    """セル群がテーブルの区切り行（`|---|` 形式）かどうかを判定。"""
    return (bool(cells) and len(cells) == len(COLS)
            and all(c and set(c) <= set("-: ") for c in cells))


def read_ledger(path: str):
    """(preamble_text, ordered_rows) を返す。rows は COLS をキーとする dict のリスト。

    実際のテーブルは、COLS ヘッダー行の直後に `|---|` 区切り行が続く
    最後の位置でアンカーされる。そのヘッダーより前はすべて preamble で、
    区切り行以降の行のみがデータ。最後の header+separator でアンカーする
    （write_ledger は常に1つだけ追加する）ため、preamble に引用された
    偽のテーブル骨組みは preamble に留まり、データに漏れず、ラウンドトリップ
    で重複もしない（ISSUE-07）。header+separator がない台帳は0行になる
    （フェイルセーフ: 曖昧なテーブルは推測しない）。
    """
    if not os.path.exists(path):
        return DEFAULT_PREAMBLE, []
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    header_idx = None
    for i in range(len(lines) - 1):
        if _split_row(lines[i]) == COLS and _is_separator(_split_row(lines[i + 1])):
            header_idx = i  # 最後に現れた header+separator ペアを保持

    rows, preamble_lines = [], lines
    if header_idx is not None:
        preamble_lines = lines[:header_idx]
        for line in lines[header_idx + 2:]:  # headerとseparatorをスキップ
            cells = _split_row(line)
            if cells and len(cells) == len(COLS) and HASH_RE.match(cells[3]):
                rows.append(dict(zip(COLS, cells)))
    preamble = "\n".join(preamble_lines).rstrip("\n") + "\n\n"
    return (preamble if preamble.strip() else DEFAULT_PREAMBLE), rows


def index(rows) -> dict:
    """行リストを {term: row} のインデックスに変換。"""
    return {r["term"]: r for r in rows}


def write_ledger(path: str, preamble: str, rows) -> None:
    """台帳をファイルに書き出す。パイプをエスケープし、改行を空白に圧縮。"""
    def esc(v):
        # テーブル行は1行なので、改行は空白に圧縮される（損失あり、意図的）。
        # その後パイプをエスケープし、read_ledger の _split_row で
        # ラウンドトリップできるようにする（ISSUE-02）。
        return (v or "").replace("\r", " ").replace("\n", " ").replace("|", r"\|")
    out = [preamble.rstrip("\n"), "",
           "| " + " | ".join(COLS) + " |",
           "|" + "|".join(["---"] * len(COLS)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(esc(r.get(c, "")) for c in COLS) + " |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def list_gaps(ledger_path: str) -> list:
    """explained=no と判定された用語——アクションすべき出力。"""
    _, rows = read_ledger(ledger_path)
    return [r for r in rows if r.get("explained", "").strip().lower() == "no"]


def record_judgment(ledger_path: str, term: str, category=None, explained=None,
                    notes=None, paths=None, **scan_kw) -> str:
    """用語の評定を台帳にupsert（挿入または更新）する。

    台帳にない新規用語の行を作成するには `paths` が必要（初出位置を特定するため）。
    更新時に `paths` を渡すと first_seen/hash も再同期され、MOVED 用語の
    再判断でクリアされる（ISSUE-01）。戻り値: "created" | "updated" | "error: ..."。
    """
    preamble, rows = read_ledger(ledger_path)
    row = index(rows).get(term)
    if row is None:
        if not paths:
            return "error: new term needs paths to locate first occurrence"
        occ = scan(paths, **scan_kw).get(term)
        if not occ:
            return "error: term not found in given paths"
        row = {"term": term, "category": category or "",
               "first_seen": fmt_seen(occ["file"], occ["line"], occ["heading"],
                                      occ.get("page", 0)),
               "hash": occ["hash"], "explained": explained or "", "notes": notes or ""}
        rows.append(row)
        action = "created"
    else:
        if category is not None:
            row["category"] = category
        if explained is not None:
            row["explained"] = explained
        if notes is not None:
            row["notes"] = notes
        if paths:
            occ = scan(paths, **scan_kw).get(term)
            if occ:
                row["first_seen"] = fmt_seen(occ["file"], occ["line"], occ["heading"],
                                               occ.get("page", 0))
                row["hash"] = occ["hash"]
        action = "updated"
    write_ledger(ledger_path, preamble, rows)
    return action


def generate_index(ledger_path: str) -> "list[tuple[str, str]]":
    """台帳から索引（用語 -> ページ番号/位置）を生成する。

    戻り値: [(term, first_seen), ...] のリスト。用語でソート済み。
    first_seen は `ファイル名:行番号 §見出し` 形式（Markdown）、
    PDFの場合は `ファイル名:pページ番号 §見出し` 形式。
    """
    _, rows = read_ledger(ledger_path)
    return sorted([(r["term"], r["first_seen"]) for r in rows],
                  key=lambda kv: kv[0])
