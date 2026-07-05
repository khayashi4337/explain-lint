"""抽出ポリシー、台帳スキーマ、共有設定の定義。

explain-lint 全体で使う定数の唯一の真実の参照元。CLI・MCPサーバー・
ドキュメントが同期しなくなるのを防ぐ（ISSUE-06）。
"""
import re

# --- 抽出ポリシー（scan() のデフォルトと CLI で共有する最小文字数） ---
DEFAULT_MIN_KANA = 3   # カタカナ連続として扱う最小文字数
DEFAULT_MIN_LATIN = 3  # ラテン文字の単語・略語として扱う最小文字数
DEFAULT_MIN_KANJI = 2  # 漢字・ひらがな混在用語の最小文字数（形態素解析時）

# 形態素解析で抽出対象とする品詞（Janomeの品詞体系）
# 名詞のみを対象とし、代名詞・非自立名詞・数詞は除外する。
MORPH_TARGET_POS = ("名詞",)
MORPH_EXCLUDE_POS1 = ("代名詞", "数", "非自立", "接尾")

# ストップワード: 一般名詞のノイズ（ひらがな1-2文字、一般的すぎる語）
MORPH_STOPWORDS = frozenset({
    "もの", "こと", "とき", "ところ", "よう", "ほう", "うち",
    "これ", "それ", "あれ", "どれ", "ここ", "そこ", "あそこ",
    "ため", "はず", "わけ", "まま", "つもり", "かわり",
    "ひと", "ひとつ", "ふたつ",
    "上", "下", "中", "外", "内", "間", "前", "後", "左", "右",
    "今", "今日", "明日", "昨日",
})

KATAKANA = re.compile(r"[ァ-ヴー]+")
# 大文字始まりの単語。-/& でつながる後続の大文字パートも取り込み、
# `AT&T`, `R&D`, `Peacock-Hall`, `Runge-Kutta` をそれぞれ1用語として扱う。
# 個々のパートは1文字でもよい（`AT&T` の A/T など）。マッチ全体が min_latin
# で長さフィルタされ、無意味な "A"/"I" は弾かれつつ短い略語は通過する。
# 大文字始まりのみを対象とする設計（小文字の専門用語はスコープ外）。
LATIN = re.compile(r"\b[A-Z][A-Za-z]*(?:[-&][A-Z][A-Za-z]*)*\b")
# 漢字・ひらがなの連続（形態素解析なしのフォールバック用）。
# 形態素解析が利用できない場合、これで粗く抽出する。
KANJI_KANA = re.compile(r"[一-龥ぁ-ゟ]+")
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
