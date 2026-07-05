"""用語抽出: 各用語の初出を検出し、コンテキストとともに記録する。"""
import hashlib
import os
import re
from typing import Optional, TypedDict

from .patterns import (DEFAULT_MIN_KANA, DEFAULT_MIN_KANJI, DEFAULT_MIN_LATIN,
                       HASH_LEN, HEADING, KANJI_KANA, KATAKANA, LATIN,
                       MORPH_EXCLUDE_POS1, MORPH_STOPWORDS, MORPH_TARGET_POS, STRIP)


class Occurrence(TypedDict):
    file: str
    line: int          # 絶対行番号（PDFは全ページ通算、Markdownはファイル内行番号）
    page: int          # PDFのページ番号（Markdownは0）
    heading: str
    hash: str
    text: str


def normalize(line: str) -> str:
    """行の空白を正規化する（前後の空白を削除し、連続空白を1スペースに圧縮）。"""
    return re.sub(r"\s+", " ", line.strip())


def line_hash(line: str) -> str:
    """行テキストの正規化後の内容からMD5ハッシュを生成し、先頭 HASH_LEN 文字を返す。"""
    return hashlib.md5(normalize(line).encode("utf-8")).hexdigest()[:HASH_LEN]


def fmt_seen(fname: str, line: int, heading: str, page: int = 0) -> str:
    """初出位置の文字列表現。

    Markdown: `ファイル名:行番号 §見出し`
    PDF: `ファイル名:pページ番号 §見出し`
    """
    loc = f"p{page}" if page > 0 else str(line)
    return f"{fname}:{loc}" + (f" §{heading}" if heading else "")


# 形態素解析器（Janome）の遅延初期化。インストールされていない場合は None。
# コアの「依存関係なし」を維持するため、janome はオプション依存。
_tokenizer = None


def _get_tokenizer():
    """Janomeのトークナイザを遅延初期化して返す。未インストールなら None。"""
    global _tokenizer
    if _tokenizer is None:
        try:
            from janome.tokenizer import Tokenizer
            _tokenizer = Tokenizer()
        except ImportError:
            _tokenizer = False  # インストールされていない
    return _tokenizer if _tokenizer is not False else None


def _morph_terms(text: str, min_kanji: int = DEFAULT_MIN_KANJI) -> set:
    """形態素解析で名詞を抽出し、ストップワードと短すぎる語を除外する。

    Janomeが未インストールの場合は KANJI_KANA 正規表現にフォールバックする。
    カタカナ用語は KATAKANA 正規表現で既に抽出されるため、ここでは漢字・ひらがな
    を含む名詞のみを返す（カタカナのみの名詞は除外）。
    """
    tok = _get_tokenizer()
    if tok is None:
        # フォールバック: 正規表現で漢字・ひらがな連続を抽出
        return {t for t in KANJI_KANA.findall(text) if len(t) >= min_kanji}
    terms = set()
    for token in tok.tokenize(text):
        pos = token.part_of_speech.split(",")
        if pos[0] not in MORPH_TARGET_POS:
            continue
        if len(pos) > 1 and pos[1] in MORPH_EXCLUDE_POS1:
            continue
        surface = token.surface
        if surface in MORPH_STOPWORDS:
            continue
        if len(surface) < min_kanji:
            continue
        # カタカナのみの語は KATAKANA 正規表現で抽出されるため重複を避ける
        if KATAKANA.fullmatch(surface):
            continue
        terms.add(surface)
    return terms


def _read_lines(path: str) -> "list[tuple[int, str]]":
    """ファイルを読み込み、(絶対行番号, 行テキスト) のリストを返す。

    PDFファイルの場合はpypdfでページごとにテキストを抽出し、全ページを通した
    連続行番号を割り当てる。Markdown/テキストファイルの場合は従来通り行番号を使う。
    pypdfが未インストールでPDFが入力された場合は空リストを返す。
    ファイルが存在しない場合はFileNotFoundErrorを投げる。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"file not found: {path}")
    if path.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return []
        reader = PdfReader(path)
        result = []
        abs_line = 0
        for page in reader.pages:
            text = page.extract_text() or ""
            for line in text.split("\n"):
                abs_line += 1
                result.append((abs_line, line))
        return result
    with open(path, encoding="utf-8") as f:
        return [(i, line) for i, line in enumerate(f.read().split("\n"), 1)]


def _read_context_lines(path: str) -> "list[str]":
    """コンテキスト取得用にファイルを行リストとして返す（PDF含む）。"""
    return [line for _, line in _read_lines(path)]


def _build_page_map(path: str) -> "dict[int, int]":
    """PDFの絶対行番号→ページ番号のマッピングを返す。Markdownの場合は空dict。

    PDFでは行番号→ページ番号の対応が必要（fmt_seen で pN 形式にするため）。
    """
    if not path.lower().endswith(".pdf"):
        return {}
    try:
        from pypdf import PdfReader
    except ImportError:
        return {}
    reader = PdfReader(path)
    page_map = {}
    abs_line = 0
    for page_num, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        for _ in text.split("\n"):
            abs_line += 1
            page_map[abs_line] = page_num
    return page_map


def scan(paths, use_kana: bool = True, use_latin: bool = True,
         use_morph: bool = False,
         min_kana: int = DEFAULT_MIN_KANA,
         min_latin: int = DEFAULT_MIN_LATIN,
         min_kanji: int = DEFAULT_MIN_KANJI) -> "dict[str, Occurrence]":
    """全パスを走査し、各用語の初出を {用語: Occurrence} として返す。

    複数ファイルを指定した場合は読み順で処理し、各用語の最初の登場位置を記録する。
    フェンスコードブロック内の行はスキップし、見出し行は直近の見出しとして記憶する。

    use_morph が True の場合、形態素解析（Janome）で漢字・ひらがなの名詞を抽出する。
    Janomeが未インストールの場合は正規表現にフォールバックする。
    """
    first: "dict[str, Occurrence]" = {}
    for path in paths:
        lines = _read_lines(path)
        fname = os.path.basename(path)
        is_pdf = path.lower().endswith(".pdf")
        if is_pdf:
            page_map = _build_page_map(path)
        heading, in_code = "", False
        for i, raw in lines:
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
            if use_morph:
                terms |= _morph_terms(clean, min_kanji=min_kanji)
            page = page_map.get(i, 0) if is_pdf else 0
            for t in terms:
                if t not in first:
                    first[t] = {"file": fname, "line": i, "page": page,
                                "heading": heading,
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
            lines = _read_context_lines(path)
            lo = max(1, occ["line"] - window)
            hi = min(len(lines), occ["line"] + window)
            ctx = [{"n": n, "text": lines[n - 1]} for n in range(lo, hi + 1)]
            return {"term": term,
                    "first_seen": fmt_seen(occ["file"], occ["line"], occ["heading"],
                                           occ.get("page", 0)),
                    "file": occ["file"], "line": occ["line"],
                    "page": occ.get("page", 0),
                    "heading": occ["heading"],
                    "hash": occ["hash"], "line_text": occ["text"], "context": ctx}
    return None
