# explain-lint ledger

- Machine-maintained first-occurrence table. explain-lint diffs the text
  against this file; only NEW/MOVED terms need a fresh judgment.
- Edit `category` / `explained` / `notes` by hand or with an LLM.
- `first_seen` line numbers are auto-updated by `--sync`.

| term | category | first_seen | hash | explained | notes |
|---|---|---|---|---|---|
| ギャップ | exclude | sample_ja.md:1 §例: 説明ギャップのある日本語技術文書 | 960a693e | na | 見出し内の語 |
| マルコフ | needs-explanation | sample_ja.md:5 §はじめに | 03c21554 | yes | 初出でインライン説明あり |
| システム | exclude | sample_ja.md:5 §はじめに | 03c21554 | na | 一般名詞 |
| リンドブラッド | needs-explanation | sample_ja.md:6 §はじめに | a4c53307 | no | GAP: 説明なしで使用 |
| ステップ | exclude | sample_ja.md:6 §はじめに | a4c53307 | na | 一般名詞 |
| モデル | exclude | sample_ja.md:6 §はじめに | a4c53307 | na | 一般名詞 |
| オブザーバブル | needs-explanation | sample_ja.md:14 §手法 | 6ee9a623 | no | GAP: 説明なし |
| コヒーレンス | needs-explanation | sample_ja.md:14 §手法 | 6ee9a623 | no | GAP: 説明なし |
| フーリエ | needs-explanation | sample_ja.md:15 §手法 | 36e6b2ec | no | GAP: 説明なし |
| スペクトル | exclude | sample_ja.md:15 §手法 | 36e6b2ec | na | 一般名詞 |
| ハミルトニアン | needs-explanation | sample_ja.md:23 §議論 | ed08fa1c | yes | 初出で説明あり |
| エネルギー | exclude | sample_ja.md:23 §議論 | ed08fa1c | na | 一般名詞 |
| パウリ | needs-explanation | sample_ja.md:23 §議論 | ed08fa1c | no | GAP: 説明なし |
