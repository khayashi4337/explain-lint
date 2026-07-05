# ISSUE-14: get_context() がPDF入力で壊れる（ページ番号を行インデックスとして誤用）

## 深刻度
高

## 概要
`get_context()` は `occ["line"]` を使ってコンテキスト行を取得するが、
PDFの場合 `occ["line"]` はページ番号（例: 1）である。
一方 `_read_context_lines()` は全ページの全行をフラットなリストで返すため、
`lines[occ["line"] - 1]` は「ページ番号番目の行」を指してしまい、
実際の用語出現箇所とは全く異なる行がコンテキストとして返される。

## 再現
```python
import explain_lint as e
ctx = e.get_context("Fourier", ["examples/sample.pdf"], window=2)
# Fourier は実際は10行目付近にあるが、ctx["context"] は1〜3行目を返す
# ctx["line"] == 1（ページ番号）
```

## 期待される挙動
PDFの場合、用語が見つかったページの前後ページ（または同一ページの前後行）を
コンテキストとして返すべき。

## 影響範囲
- `extract.py`: `get_context()`
- `explain_lint_mcp.py`: `get_term_context` ツール

## 修正方針
- `_read_lines()` の戻り値にページ内行番号または絶対行位置を含める
- `get_context()` でPDFの場合はページ単位でコンテキストを取得する
- または `Occurrence` にページ内オフセットを追加する

## branch
`fix/14-pdf-context-broken`
