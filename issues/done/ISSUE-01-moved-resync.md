# ISSUE-01 MOVED語がrecord_judgment後も消えない（差分ループが閉じない）

- **深刻度**: 高（ツールの存在意義に直結）
- **分類**: 正当性
- **branch**: fix/01-moved-resync

## 症状
初出行が書き換わった語（MOVED）を、AIが `record_judgment(explained=...)` で判定しても、次回 `lint_report`/`report` で MOVED のまま残り続ける。差分駆動の売り（判定したら黙る）が MOVED で機能しない。

## 再現（実測済み）
1. 初出行を書き換える → report で MOVED 検出
2. `record_judgment(term, explained='yes', paths=[...])` → "updated"
3. 再度 report → **同じ語がまだ MOVED**

## 根本原因
`explain_lint.py` の `record_judgment` の「update」分岐が `category`/`explained`/`notes` のみ書き換え、`first_seen`/`hash` を更新しない。`paths` を渡しても無視される。sync も hash 一致時のみ first_seen を更新（hash自体は更新しない）ため、MOVED（hash変化）を解消する経路がどこにも無い。

## 修正方針
`record_judgment` の update 分岐で、`paths` が与えられたら `scan` し直し、その語の現在の `first_seen`/`hash` を再計算して行に反映する。判定の記録と位置の再同期を同一操作にする。MCP の `record_judgment` からも paths を渡せるようにする。

## 完了条件（回帰テスト）
- `test_diff_lifecycle`: reword→MOVED→record_judgment(paths)→再 diff で **MOVED が消え matched になる**。
- NEW→judgment→matched も同テストで確認。
- 既存 CLI/MCP の互換維持（report/gaps/sync のexit・出力不変）。
