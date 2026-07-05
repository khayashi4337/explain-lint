# ISSUE-12: scan()がファイル不在時の例外をハンドリングしない

## 深刻度
中

## 概要
`extract.py` の `_read_lines()` は、ファイルが存在しない場合に未処理の例外を投げる。
Markdownの場合は `open(path)` が `FileNotFoundError`、PDFの場合は `PdfReader(path)` が同様に例外を投げる。
ISSUE-08でPDF対応を追加したことで、このパスに到達するケースが増えたが、
根本的な問題はISSUE-01〜07の時から存在していた（既存バグ）。

## 再現
```bash
python -m explain_lint nonexistent.md --dump
# → FileNotFoundError のトレースバックが出る
```

## 期待される挙動
ファイルが存在しない場合は、わかりやすいエラーメッセージを表示して終了する
（トレースバックではなく、CLIのエラーメッセージとして）。

## 影響範囲
- `extract.py`: `_read_lines()`, `scan()`, `get_context()`
- `cli.py`: 各モード（`--dump`, `--sync`, デフォルト）
- `explain_lint_mcp.py`: 各ツール

## 修正方針
- `_read_lines()` の冒頭で `os.path.exists()` チェック、または
  `try/except FileNotFoundError` で空リストを返す
- CLI側でファイル不在時にユーザーフレンドリーなエラーメッセージを表示

## branch
`fix/12-scan-file-not-found`
