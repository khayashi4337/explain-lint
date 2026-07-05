# ISSUE-16: MCPサーバーに索引生成ツールがない

## 深刻度
低

## 概要
ISSUE-08で `generate_index()` 関数とCLI `--index` オプションを追加したが、
MCPサーバー（`explain_lint_mcp.py`）に同等のツールが定義されていない。
LLMクライアントから索引生成を利用できない。

## 期待される挙動
MCPサーバーに `generate_index(ledger)` ツールが存在し、
台帳から索引（用語→ページ/行位置）を返すべき。

## 影響範囲
- `explain_lint_mcp.py`: ツール定義が不足

## 修正方針
```python
@mcp.tool()
def generate_index(ledger: str) -> dict:
    """台帳から索引（用語→位置）を生成する。"""
    entries = core.generate_index(ledger)
    return {"count": len(entries),
            "index": [{"term": t, "first_seen": s} for t, s in entries]}
```

## branch
`fix/16-mcp-index-tool`
