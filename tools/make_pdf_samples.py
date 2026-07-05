"""ISSUE-11: PDFサンプルを生成するスクリプト（開発時のみ使用）。

examples/sample.md と examples/sample_ja.md の内容からPDFを生成する。
生成済みPDFをリポジトリにコミットするため、通常はこのスクリプトを再実行する必要はない。
"""
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _make_pdf(path, lines, font="Helvetica", font_size=12):
    """テキスト行のリストからシンプルなPDFを生成する。"""
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - inch
    line_height = font_size + 4
    c.setFont(font, font_size)
    for line in lines:
        if y < inch:
            c.showPage()
            c.setFont(font, font_size)
            y = height - inch
        if line.startswith("# "):
            c.setFont(font + "-Bold", font_size + 4)
            c.drawString(inch, y, line[2:])
            c.setFont(font, font_size)
            y -= line_height + 4
        elif line.startswith("## "):
            c.setFont(font + "-Bold", font_size + 2)
            c.drawString(inch, y, line[3:])
            c.setFont(font, font_size)
            y -= line_height + 2
        elif line.strip() == "":
            y -= line_height // 2
        else:
            c.drawString(inch, y, line)
            y -= line_height
    c.save()


def main():
    # 英語サンプルPDF
    en_lines = [
        "# Example: an article with an explanation gap",
        "",
        "## Introduction",
        "",
        "We model the system as a Markov chain (a process where the next state",
        "depends only on the current one, not the full history). Each step applies a",
        "Lindblad map to the density matrix.",
        "",
        'Here "Markov chain" is explained on first use. "Lindblad" and "density matrix"',
        "are not -- a reader meeting them here is stuck. That is the gap explain-lint",
        "surfaces.",
        "",
        "## Method",
        "",
        "The observable is measured, and coherence decays over time. We then",
        "apply a Fourier transform to recover the spectrum.",
        "",
        'The terms "coherence" and "Fourier" arrive with no gloss.',
        "",
    ]
    _make_pdf(os.path.join(REPO, "examples", "sample.pdf"), en_lines)

    # 日本語サンプルPDF（日本語フォントが必要なため、カタカナ・ラテンのみ）
    ja_lines = [
        "# Example: Japanese technical article",
        "",
        "## Introduction",
        "",
        "The system uses Markov chain and Lindblad operators.",
        "The density matrix is key to the analysis.",
        "",
        "## Method",
        "",
        "The observable is measured, and coherence decays.",
        "Fourier transform is applied to recover the spectrum.",
        "",
        "## Discussion",
        "",
        "The Hamiltonian represents total energy.",
        "Pauli matrices are left as an exercise.",
        "",
    ]
    _make_pdf(os.path.join(REPO, "examples", "sample_ja.pdf"), ja_lines)

    print("Generated: examples/sample.pdf, examples/sample_ja.pdf")


if __name__ == "__main__":
    main()
