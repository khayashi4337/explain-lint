"""ISSUE-04: extraction policy — abbreviations, min-length params, exclusions.

The old LATIN regex hard-coded English capitalized-3+-chars and could not
capture `AT&T` / `R&D` (a proper-noun tracker structurally missing canonical
proper nouns). Min length was split between the regex (Latin) and a param
(kana). This consolidates the policy and fixes the abbreviation miss.
"""
import explain_lint as e


def _terms(tmp_path, text, **kw):
    doc = tmp_path / "d.md"
    doc.write_text(text, encoding="utf-8")
    return set(e.scan([str(doc)], **kw).keys())


def test_abbreviations_captured(tmp_path):
    t = _terms(tmp_path, "AT&T and R&D and Peacock-Hall and Runge-Kutta appear.\n")
    assert "AT&T" in t
    assert "R&D" in t
    assert "Peacock-Hall" in t
    assert "Runge-Kutta" in t


def test_single_and_short_capitals_filtered(tmp_path):
    # min_latin=3 (default): stray single caps and 2-letter words are noise.
    t = _terms(tmp_path, "I think A cat and Dr Smith wrote Nice things.\n")
    assert "I" not in t and "A" not in t and "Dr" not in t
    assert "Nice" in t and "Smith" in t


def test_min_latin_param(tmp_path):
    assert "Go" not in _terms(tmp_path, "Go Foo now.\n", min_latin=3)
    assert "Go" in _terms(tmp_path, "Go Foo now.\n", min_latin=2)
    assert "Foo" in _terms(tmp_path, "Go Foo now.\n", min_latin=3)


def test_min_kana_param(tmp_path):
    txt = "コア オブザーバブル\n"  # コア=2 chars, オブザーバブル=7
    assert "コア" not in _terms(tmp_path, txt, min_kana=3)
    assert "コア" in _terms(tmp_path, txt, min_kana=2)
    assert "オブザーバブル" in _terms(tmp_path, txt, min_kana=3)


def test_cap_lowercase_hyphen_not_overcaptured(tmp_path):
    # "Foo-bar" (cap-then-lowercase) is not a joined proper noun; capture "Foo".
    t = _terms(tmp_path, "The Foo-bar thing.\n")
    assert "Foo" in t
    assert "Foo-bar" not in t


def test_lowercase_start_still_excluded(tmp_path):
    # capitalized-only remains the default; lowercase jargon is not captured.
    t = _terms(tmp_path, "a qubit and an eigenvalue.\n")
    assert "qubit" not in t and "eigenvalue" not in t


def test_exclusions_still_hold(tmp_path):
    # code fence / inline code / $math$ / URL must still be excluded.
    txt = (
        "# H\n\n"
        "Real Term here.\n"
        "`InlineCode` and $MathSym$ and https://Example.com/Path\n"
        "```\nFencedTerm\n```\n"
    )
    t = _terms(tmp_path, txt)
    assert "Term" in t
    assert "InlineCode" not in t
    assert "MathSym" not in t
    assert "FencedTerm" not in t
