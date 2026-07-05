"""用語抽出: 各用語の初出を検出し、コンテキストとともに記録する。"""
import hashlib
import os
import re
from typing import Optional, TypedDict

from .patterns import (DEFAULT_MIN_KANA, DEFAULT_MIN_LATIN, HASH_LEN, HEADING,
                       KATAKANA, LATIN, STRIP)


class Occurrence(TypedDict):
    file: str
    line: int
    heading: str
    hash: str
    text: str


def normalize(line: str) -> str:
    """行の空白を正規化する（前後の空白を削除し、連続空白を1スペースに圧縮）。"""
    return re.sub(r"\s+", " ", line.strip())


def line_hash(line: str) -> str:
    """行テキストの正規化後の内容からMD5ハッシュを生成し、先頭 HASH_LEN 文字を返す。"""
    return hashlib.md5(normalize(line).encode("utf-8")).hexdigest()[:HASH_LEN]


def fmt_seen(fname: str, line: int, heading: str) -> str:
    """初出位置の文字列表現: `ファイル名:行番号 §見出し`（見出しなければ省略）。"""
    return f"{fname}:{line}" + (f" §{heading}" if heading else "")


def scan(paths, use_kana: bool = True, use_latin: bool = True,
         min_kana: int = DEFAULT_MIN_KANA,
         min_latin: int = DEFAULT_MIN_LATIN) -> "dict[str, Occurrence]":
    """全パスを走査し、各用語の初出を {用語: Occurrence} として返す。

    複数ファイルを指定した場合は読み順で処理し、各用語の最初の登場位置を記録する。
    フェンスコードブロック内の行はスキップし、見出し行は直近の見出しとして記憶する。
    """
    first: "dict[str, Occurrence]" = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        fname = os.path.basename(path)
        heading, in_code = "", False
        for i, raw in enumerate(lines, 1):
            if raw.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            hm = HEADING.match(raw)
            if hm:
                heading = hm.group(2).strip()
            clean = raw
            for pat in STRIP:
                clean = pat.sub(" ", clean)
            terms = set()
            if use_kana:
                terms |= {t for t in KATAKANA.findall(clean) if len(t) >= min_kana}
            if use_latin:
                terms |= {t for t in LATIN.findall(clean) if len(t) >= min_latin}
            for t in terms:
                if t not in first:
                    first[t] = {"file": fname, "line": i, "heading": heading,
                                "hash": line_hash(raw), "text": raw.strip()}
    return first


def get_context(term: str, paths, window: int = 2, **scan_kw) -> Optional[dict]:
    """指定用語の初出とその前後 `window` 行のコンテキストを返す。

    戻り値: {term, first_seen, file, line, heading, hash, line_text,
    context:[{n,text}...]}。用語が一度も出現しない場合は None。
    """
    occ = scan(paths, **scan_kw).get(term)
    if not occ:
        return None
    for path in paths:
        if os.path.basename(path) == occ["file"]:
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
            lo = max(1, occ["line"] - window)
            hi = min(len(lines), occ["line"] + window)
            ctx = [{"n": n, "text": lines[n - 1]} for n in range(lo, hi + 1)]
            return {"term": term,
                    "first_seen": fmt_seen(occ["file"], occ["line"], occ["heading"]),
                    "file": occ["file"], "line": occ["line"], "heading": occ["heading"],
                    "hash": occ["hash"], "line_text": occ["text"], "context": ctx}
    return None
