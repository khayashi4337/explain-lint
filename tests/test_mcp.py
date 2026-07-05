"""ISSUE-16: MCPサーバーに索引生成ツールがあることを確認する。

MCPサーバー（explain_lint_mcp.py）は mcp パッケージに依存するため、
インポートには mcp が必要。mcp が未インストールの場合はスキップする。
"""
import importlib


def _has_mcp():
    try:
        import mcp
        return True
    except ImportError:
        return False


def test_mcp_has_generate_index():
    # MCPサーバーに generate_index ツールが定義されていること。
    if not _has_mcp():
        return
    mod = importlib.import_module("explain_lint_mcp")
    # FastMCP のツール登録はデコレータで行われるため、関数オブジェクトの存在を確認
    assert hasattr(mod, "generate_index")
    assert callable(mod.generate_index)


def test_mcp_generate_index_returns_dict(tmp_path):
    # generate_index ツールが正しい形式のdictを返すこと。
    if not _has_mcp():
        return
    import explain_lint as e
    mod = importlib.import_module("explain_lint_mcp")
    doc = tmp_path / "d.md"
    doc.write_text("# Head\n\nThe オブザーバブル here.\n", encoding="utf-8")
    ledger = tmp_path / "d.md.terms.md"
    e.record_judgment(str(ledger), "オブザーバブル", explained="no", paths=[str(doc)])
    result = mod.generate_index(str(ledger))
    assert isinstance(result, dict)
    assert result["count"] == 1
    assert result["index"][0]["term"] == "オブザーバブル"
