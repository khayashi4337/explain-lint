"""リポジトリルートをインポート可能にし、テストで `import explain_lint` できるようにする。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
