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
| ISSUE-08 | 機能要望 | PDF対応 + 索引（back-of-book index）生成 | feature/08-pdf-index | ✅done |
| ISSUE-09 | 機能要望 | 日本語漢字・ひらがな用語の抽出（形態素解析） | feature/09-ja-morphological | ✅done |
| ISSUE-10 | 機能要望 | 日本語サンプルの追加 | feature/10-ja-sample | ✅done |
| ISSUE-11 | 機能要望 | PDFサンプルの追加（ISSUE-08依存） | feature/11-pdf-sample | ✅done |
| ISSUE-12 | 中 | scan()がファイル不在時の例外を未ハンドリング（既存バグ） | fix/12-scan-file-not-found | ✅done |
| ISSUE-13 | 低 | レビュー3回イテレートのスキップ（ISSUE-08〜11） | — | open |
| ISSUE-14 | 高 | get_context()がPDF入力で壊れる（ページ番号を行インデックスとして誤用） | fix/14-pdf-context-broken | ✅done |
| ISSUE-15 | 中 | フォールバック形態素解析が極めてノイズが多い（文全体が1用語になる） | fix/15-fallback-morph-noise | ✅done |
| ISSUE-16 | 低 | MCPサーバーに索引生成ツールがない | fix/16-mcp-index-tool | ✅done |
