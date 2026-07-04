# explain-lint issue tracking

Code-review findings (2026-07) tracked as issues. GitHub 未接続のため、当面は
このフォルダで管理する（push 後に GitHub Issues へ移行可能）。

## ワークフロー（senior-engineer discipline）

1. 1 issue = 1 branch（`fix/NN-slug`）。main への直コミット禁止（tracking docs を除く）。
2. **コミット時に 3 回レビュー**（セバス様）: 1回目=必須（バグ根治・回帰テスト有無）／2回目=優先高（整合・エッジ）／3回目=優先中（スタイル・命名）。REJECTED は是正して再レビュー。
3. **PR（= main への merge）時に 3 回レビュー**: 1回目=変更の正確さ・スコープ／2回目=他部分への波及／3回目=完了条件保持。全 APPROVED で merge。
4. 各 fix は回帰テストを同梱（test-driven bug fix）。
5. 全 issue done 後、林さんがレビュー。

## 状態

- `open/` = 未着手・作業中
- `done/` = merge 済み

## 一覧（深刻度順）

| ID | 深刻度 | 概要 | branch | 状態 |
|---|---|---|---|---|
| ISSUE-01 | 高 | MOVED語がrecord_judgment後も消えない（hash非再同期） | fix/01-moved-resync | ✅done |
| ISSUE-02 | 高 | セル内`\|`で台帳の行が消失（非対称エスケープ） | fix/02-ledger-pipe | ✅done |
| ISSUE-03 | 高 | 非UTF8コンソールで出力クラッシュ（`—`/`§`） | fix/03-unicode-output | ✅done |
| ISSUE-04 | 高 | 抽出方針のハードコーディング（AT&T漏れ・大文字限定・最小長分散） | fix/04-extraction-config | ✅done |
| ISSUE-05 | 中 | 自動テスト不在 | fix/05-tests | ✅done |
| ISSUE-06 | 中 | 1ファイル集約→パッケージ分割＋定数一元化 | fix/06-package-split | ✅done |
| ISSUE-07 | 低 | preamble内の表行をデータ行と誤認（ISSUE-02レビュー由来） | fix/07-preamble-robustness | ✅done |
