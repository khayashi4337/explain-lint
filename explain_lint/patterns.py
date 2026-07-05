"""抽出ポリシー、台帳スキーマ、共有設定の定義。

explain-lint 全体で使う定数の唯一の真実の参照元。CLI・MCPサーバー・
ドキュメントが同期しなくなるのを防ぐ（ISSUE-06）。
"""
import re

# --- 抽出ポリシー（scan() のデフォルトと CLI で共有する最小文字数） ---
DEFAULT_MIN_KANA = 3   # カタカナ連続として扱う最小文字数
DEFAULT_MIN_LATIN = 3  # ラテン文字の単語・略語として扱う最小文字数

KATAKANA = re.compile(r"[ァ-ヴー]+")
# 大文字始まりの単語。-/& でつながる後続の大文字パートも取り込み、
# `AT&T`, `R&D`, `Peacock-Hall`, `Runge-Kutta` をそれぞれ1用語として扱う。
# 個々のパートは1文字でもよい（`AT&T` の A/T など）。マッチ全体が min_latin
# で長さフィルタされ、無意味な "A"/"I" は弾かれつつ短い略語は通過する。
# 大文字始まりのみを対象とする設計（小文字の専門用語はスコープ外）。
LATIN = re.compile(r"\b[A-Z][A-Za-z]*(?:[-&][A-Z][A-Za-z]*)*\b")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
# 用語抽出前に取り除くスパン（数式・コード・画像・URL は用語を含まない）。
STRIP = [
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\$[^$\n]*\$"),
    re.compile(r"`[^`\n]*`"),
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    re.compile(r"https?://\S+|10\.\d{4,}/\S+"),
]

# --- 台帳スキーマ ---
HASH_LEN = 8                     # 行内容ハッシュの長さ（16進文字数）
HASH_RE = re.compile(rf"^[0-9a-f]{{{HASH_LEN}}}$")
PIPE_SPLIT = re.compile(r"(?<!\\)\|")  # エスケープされていない | のみで行を分割
COLS = ["term", "category", "first_seen", "hash", "explained", "notes"]
TERMS_SUFFIX = ".terms.md"       # デフォルト台帳パス = <最初の入力> + この接尾辞
DEFAULT_PREAMBLE = (
    "# explain-lint ledger\n\n"
    "- Machine-maintained first-occurrence table. explain-lint diffs the text\n"
    "  against this file; only NEW/MOVED terms need a fresh judgment.\n"
    "- Edit `category` / `explained` / `notes` by hand or with an LLM.\n"
    "- `first_seen` line numbers are auto-updated by `--sync`.\n\n"
)
