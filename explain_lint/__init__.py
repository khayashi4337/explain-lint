"""explain-lint — 文章中の未説明用語を見つけるリンター。

目的
    コンパイラは「未定義の変数」を検出する。文章にも同じバグがある——
    定義されずに使われる用語だ。AI生成テキストは特にこの問題を起こしやすく、
    流暢に専門用語を織り交ぜながら定義を一切書かない。explain-lint は文章版
    リンターである: 各用語の初出を見つけ、台帳に記録し、差分ベースで
    前回からの変化だけを抽出する。これにより「本当に説明されているか？」
    という判断（人間またはLLM）を毎回文書全体ではなく差分に対して実行できる。

レイヤー構成（1モジュール1責務）
    patterns  — 抽出ポリシー、台帳スキーマ、共有設定定数
    extract   — scan(), get_context(): 各用語の初出を検出
    ledger    — Markdown台帳の読み書き、record_judgment(), list_gaps()
    diff      — diff(), sync_linenumbers(): 差分エンジン
    cli       — コマンドラインエントリポイント（出力を行う唯一のモジュール）
    「この用語は説明が必要か？説明されているか？」という判断は、別の
    人間/LLMレイヤーの仕事——explain_lint_mcp.py を参照。

CLI
    python -m explain_lint doc.md [more.md ...] [--ledger PATH]
      (デフォルト)     NEW / MOVED / GONE を報告; NEW または MOVED で exit 1
      --dump        全用語の初出を表示（台帳のシード用）
      --sync        hash一致する用語の行番号を更新
      --gaps        台帳で explained=no と判定された用語を一覧
      --no-kana / --no-latin / --min-kana N / --min-latin N   抽出のチューニング
      --morph / --no-morph   形態素解析による漢字・ひらがな用語抽出（要: pip install explain-lint[ja]）
      --lang ja     CLIメッセージを日本語で出力（デフォルト: en）

ライセンス  MIT。「観測の窓」論文プロジェクト（2026）から派生。
"""
from .patterns import (COLS, DEFAULT_MIN_KANA, DEFAULT_MIN_KANJI, DEFAULT_MIN_LATIN,
                       DEFAULT_PREAMBLE, HASH_LEN, HASH_RE, HEADING, KANJI_KANA,
                       KATAKANA, LATIN, MORPH_EXCLUDE_POS1, MORPH_STOPWORDS,
                       MORPH_TARGET_POS, PIPE_SPLIT, STRIP, TERMS_SUFFIX)
from .extract import (Occurrence, fmt_seen, get_context, line_hash, normalize,
                      scan)
from .ledger import (default_ledger, index, list_gaps, read_ledger,
                     record_judgment, write_ledger)
from .diff import DiffResult, diff, sync_linenumbers
from .cli import main

__all__ = [
    # 抽出
    "scan", "get_context", "normalize", "line_hash", "fmt_seen", "Occurrence",
    # 台帳（private _split_row は explain_lint.ledger._split_row に存在）
    "read_ledger", "write_ledger", "index", "list_gaps", "record_judgment",
    "default_ledger",
    # 差分
    "diff", "sync_linenumbers", "DiffResult",
    # CLI
    "main",
    # 設定 / パターン
    "DEFAULT_MIN_KANA", "DEFAULT_MIN_KANJI", "DEFAULT_MIN_LATIN", "KATAKANA",
    "LATIN", "KANJI_KANA", "HEADING", "STRIP", "HASH_RE", "HASH_LEN",
    "PIPE_SPLIT", "COLS", "TERMS_SUFFIX", "DEFAULT_PREAMBLE",
    "MORPH_TARGET_POS", "MORPH_EXCLUDE_POS1", "MORPH_STOPWORDS",
]
