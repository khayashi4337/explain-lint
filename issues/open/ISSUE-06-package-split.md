# ISSUE-06 1ファイル集約→パッケージ分割＋定数一元化

- **深刻度**: 中（構造。型注釈非一貫・DRY違反・テスト書きにくさの温床）
- **分類**: 分離（＋ハードコーディング一元化）
- **branch**: fix/06-package-split

## 症状
`explain_lint.py` 約330行に「パターン定義・抽出・文脈・台帳I/O・差分・sync・gaps・record_judgment・CLIのargparseと全print整形」が同居。ライブラリ+CLI+MCP を名乗るには関心の分離が不足。`.terms.md` 既定パスが core(`main`) と mcp(`_ledger_for`) で二重定義（mcp は core を呼ばず黙って乖離しうる）。

## 修正方針（分割案）
```
explain_lint/
    __init__.py     # 公開API再エクスポート（後方互換 from explain_lint import scan, diff...）
    patterns.py     # 正規表現＋設定定数（MIN_LATIN/MIN_KANA/HASH_LEN/TERMS_SUFFIX/COLS/DEFAULT_PREAMBLE）
    extract.py      # scan/get_context/normalize/line_hash/fmt_seen
    ledger.py       # read/write/index/record_judgment/list_gaps/default_ledger
    diff.py         # diff/sync_linenumbers
    cli.py          # main（出力整形・Unicode吸収はここだけ）
explain_lint_mcp.py # core.default_ledger() を使い .terms.md 重複を解消／抽出オプションを委譲
pyproject.toml      # packages=["explain_lint"]、scripts=explain-lint="explain_lint.cli:main"
```
- `.terms.md`・最小長・hash桁を patterns.py に一元化し、CLI/MCP/README がすべて参照。
- core にも型注釈を付与、戻り値 dict を TypedDict（Occurrence/DiffResult）化し mcp と共有。
- MCP ツールに抽出オプション（use_kana 等）を追加し core へ委譲（CLI/MCP機能対称化）。

## 前提
ISSUE-01〜05 を先に完了（バグ根治とテストが緑の状態）してから構造改革に入る。分割はテストが安全網。

## 完了条件
- 分割後も `pytest` 緑・CLI/MCP 互換維持（tools/list 6件、stdio往復、report/gaps/sync）。
- `.terms.md` 定義箇所が1つだけ（grep で単一化を実測）。
- 後方互換 import（`from explain_lint import scan`）が動く。
