# ISSUE-03 非UTF8コンソールで出力がクラッシュする（素で叩くと即死）

- **深刻度**: 高（README通りに叩くと初手で死ぬ）
- **分類**: その他（移植性・Windows依存）
- **branch**: fix/03-unicode-output

## 症状
既定の `report`/`dump`/`gaps` が Windows コンソール（cp932）等の非UTF8環境で `UnicodeEncodeError` を投げて落ちる。README の Quick Start をそのまま実行すると NEW 表示行でトレースバック。

## 根本原因
出力に非ASCII装飾 `—`（em-dash, 一覧の区切り）と `§`（fmt_seen の見出し接頭）を使い、`sys.stdout` のエンコーディングが cp932 だと encode 不能。開発時は `PYTHONIOENCODING=utf-8` を付けていたため気づけなかった（＝環境依存の盲点）。

## 修正方針
- 起動時に `sys.stdout`/`sys.stderr` を `reconfigure(encoding="utf-8", errors="replace")`（Python 3.7+）。失敗時のフォールバックも用意。
- 併せて、装飾を ASCII 化できる余地（`—`→`--`）も検討。ただし `§` は first_seen の一部なので、根治は stdout の UTF-8 化。
- README の Quick Start は前提なしで動くようにする。

## 完了条件（回帰テスト）
- `test_cli`: `PYTHONIOENCODING` を空にした subprocess で `report`/`dump`/`gaps` が **exit 0/1 で正常終了し UnicodeEncodeError を出さない**。
- 出力内容（語・件数）は変わらない。
