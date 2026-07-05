# explain-lint

**文章中の未説明用語を見つけるリンター。**

コンパイラは「未定義の変数」を検出します。文章にも同じバグがあります——
定義されずに使われる用語です。AI生成テキストは特にこの問題を起こしやすく、
流暢に専門用語を織り交ぜながら定義を一切書きません。`explain-lint` は文章版
リンターです。各用語の**初出**を見つけ、台帳（ledger）に記録し、さらに
*差分ベース*で前回からの変化だけを抽出します。これにより、「本当に説明されているか？」
というコストの高い判断（人間またはLLMによる）を毎回文書全体ではなく**差分**に対して
実行できます。

> 由来: 23章からなる物理学論文から生まれました。AIレビューアが "P&H" という用語が
> 定義なしで約40回使われていることに気づいたのがきっかけです。著者の反応——
> *"自分の文章でも未定義の変数を検出できるんだ"*——がこのツールの出発点です。

## 差分アプローチが重要な理由

「すべての用語が説明されているか？」を確認するために本全体を再読するのは、
人間でもLLMでもコストがかかります。`explain-lint` は各用語の初出を**台帳**として
保持し、行番号ではなく**その行のテキストのハッシュ**をキーにします。つまり:

- 冒頭に段落を追加してすべての行番号がずれた？ **ノイズなし。** ハッシュは一致したまま、
  `--sync` が番号を黙々と書き直します。
- 用語の初出箇所を*書き換えた*？ **その用語だけ**が `MOVED` としてフラグされます——
  再判断するのはその1件だけ。
- 本当に新しい用語が登場した？ `NEW` としてフラグされます——1回判断すれば、
  以降はずっと記憶されます。

人間/LLMの判断コストが、毎回 *O(文書全体)* から *O(変更分)* に縮小します。

## インストール

純粋なPython 3、依存関係なし。

```
git clone <this repo>
python -m explain_lint your_doc.md
```

## クイックスタート

```bash
# 1. 各用語の初出をすべて表示（台帳のシード材料）
python -m explain_lint doc.md --dump

# 2. doc.md.terms.md（台帳）を作成——各用語のカテゴリ/説明状態を判定
#    （手動で、またはNEWリストをLLMに渡す）。フォーマットは後述。

# 3. 以降はこれだけ実行。変化があるまで何も出力しません:
python -m explain_lint doc.md          # exit 0 = 新規なし; exit 1 = NEW/MOVEDあり

# 行番号がずれるだけの編集後:
python -m explain_lint doc.md --sync   # 変更のない用語の行番号を書き直し
```

複数ファイルは順番に読み込まれます（章ごとに分割された本などに便利）:

```bash
python -m explain_lint ch01.md ch02.md ch03.md --ledger book.terms.md
```

## 台帳（ledger）

自分（またはLLM）が編集するプレーンなMarkdownテーブルです。ツールは最初の4列を
機械的に維持し、`explained` と `notes` はあなたが管理します。

```
| term | category | first_seen | hash | explained | notes |
|---|---|---|---|---|---|
| ホロノミー | needs-explanation | ch12.md:42 §Geometry | ab12cd34 | no  | GAP: used with no gloss |
| Markov     | needs-explanation | ch01.md:5  §Intro    | 50632610 | yes | glossed inline on first use |
| Introduction | exclude         | ch01.md:3  §Intro    | d69dd448 | na  | heading word |
```

推奨語彙（強制ではありません——単なる文字列です）:

- `category`: `needs-explanation` / `common` / `proper-noun` / `exclude`
- `explained`: `yes` / `no` / `na`

**アクションすべき出力は `explained = no`**——用語解説が必要でまだない用語です。
台帳から直接grepで抽出できます:

```bash
grep '| no |' doc.md.terms.md
```

## できること——できないこと

**できること（機械検出のコア）:**

- 候補用語の抽出: カタカナ連続（`--min-kana`、デフォルト3）および/または
  `AT&T` / `R&D` / `Peacock-Hall` のようなラテン文字の単語や略語
  （`--min-latin`、デフォルト3）。`--no-kana` / `--no-latin` で切り替え。
- 各用語の初出を記録: ファイル、行、直近の見出し、行ハッシュ。
- フェンスコード、インラインコード、`$math$`、`$$math$$`、画像タグ、URLを無視。
- 台帳との差分 → `NEW` / `MOVED` / `GONE`; NEW または MOVED で exit 1。

**できないこと（意図的）:**

- 用語が説明されているかを判断しない。その評定は台帳に書き込む別の
  人間/LLMレイヤーの仕事です。ツールは台帳をテキストに対して正直に保ち、
  新たに判断すべきものを知らせるだけです。これによりコアは決定的論理・
  オフライン・依存関係なし・監査可能に保たれ、（ファジーでモデル依存の）
  判断はあなたが制御するプラグ可能なステップとして分離されます。

## AIアシスタントから使う（MCP）

判断ステップは*AIのタスク*です——ただし差分コアがアシスタントに渡すのは
文書全体ではなくNEW/MOVED用語だけなので、コストは低いです。同梱の
**MCPサーバー**（`explain_lint_mcp.py`）がその接点です: アシスタント
（Claude等）を接続すれば、ループ全体を自律的に実行できます。

```
pip install mcp        # コアは何も不要; サーバーはこれが必要
```

登録（Claude Code / Claude Desktop の `mcpServers` 設定）:

```json
{
  "mcpServers": {
    "explain-lint": {
      "command": "python",
      "args": ["/absolute/path/to/explain-lint/explain_lint_mcp.py"]
    }
  }
}
```

アシスタントが見るツール:

| tool | purpose |
|---|---|
| `lint_report(paths, ledger)` | 差分: NEW / MOVED / GONE 用語 |
| `get_term_context(term, paths, window)` | 初出 + 周辺行を取得し、判断材料にする |
| `record_judgment(ledger, term, category, explained, notes, paths)` | 評定を台帳に書き戻す |
| `list_gaps(ledger)` | 結果: `explained = no` の用語一覧 |
| `sync_ledger(paths, ledger)` | 行番号のずれをリフレッシュ |
| `dump_terms(paths)` | すべての初出（台帳のシード用） |

アシスタントが実行するループ: **`lint_report`** → 各NEW用語について
**`get_term_context`** → 判断 → **`record_judgment`** → **`list_gaps`** で
未説明用語を報告。サーバーはモデルを持たず、API呼び出しも行いません——
知能は接続するクライアント側にあります。

## ロードマップ

完了: 決定的論理コア（CLI + インポート可能な関数）と、アシスタントが判断ループを
駆動できる**MCPサーバー**。次に構想しているもの:

- クライアントがLLMコールバックを渡すとサーバー側でループ全体を一回で実行する
  便利ツール。
- よりリッチな用語抽出（複数語のフレーズ; カナ+ラテン以外の言語パック）。
- CIアクション（新しい未説明用語がドキュメントに入ったPRを失敗にする）。
- エディタ統合（書いている最中にギャップをフラグ）。

## 開発

コアにランタイム依存関係はありません; テストには `pytest` のみが必要です:

```
pip install pytest
python -m pytest
```

テストスイート（`tests/`）は差分ライフサイクル（NEW/MOVED/GONE および
再判断されたMOVEDがクリアされること）、台帳の特殊文字ラウンドトリップ、
用語抽出と除外、`sync` の行ずれ vs 内容変更、非UTF-8コンソールでのCLI動作を
カバーしています。各テストは過去の特定バグの回帰テストでもあります——
`issues/` を参照してください。

## ライセンス

MIT — [LICENSE](LICENSE) を参照。
