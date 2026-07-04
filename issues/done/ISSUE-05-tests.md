# ISSUE-05 自動テストが存在しない（公開前の必須）

- **深刻度**: 中（回帰の歯止めが無い。高深刻度4件は全て基本ユニットテスト1本で捕まえられた）
- **分類**: テスト
- **branch**: fix/05-tests

## 症状
pytest 等の自動テストがゼロ。examples は手動確認のみ。ISSUE-01〜04 のバグはいずれも標準的なユニットテストで検出可能だった。

## 修正方針
`tests/`（pytest）を導入。標準ライブラリのみで動く形（`pip install pytest` のみ）。ISSUE-01〜04 の回帰テストはそれぞれの fix ブランチに同梱するのが基本だが、本 issue で **tests/ の土台（conftest・共通フィクスチャ・実行手順）** と、fix に紐づかない基礎テストを整備する。

## 置くべきテスト（レビュー推奨）
- `test_extract.py`: 抽出・除外・境界（ISSUE-04と協調）
- `test_ledger_roundtrip.py`: write→read 恒等・特殊文字（ISSUE-02と協調）
- `test_diff_lifecycle.py`: NEW/MOVED/GONE 遷移（ISSUE-01と協調）
- `test_sync.py`: 行ドリフト vs 文脈変更
- `test_cli.py`: exit code・非UTF8環境（ISSUE-03と協調）

## 完了条件
- `pytest` が緑。README に実行手順を追記。
- CI 化（GitHub Actions）は push 後の別 issue とする。
