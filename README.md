# explain-lint

**A linter for unexplained terms in prose.**

Compilers catch *"undefined variable."* Prose has the same bug: a term used
without ever being explained. AI-generated text is especially prone to it — it
drops jargon fluently and never defines it. `explain-lint` is the prose
analogue of a linter. It finds every term's **first occurrence**, remembers it
in a ledger, and — *differentially* — surfaces only what changed since last
time, so the expensive *"is this actually explained?"* judgment (by a human or
an LLM) runs on the **diff**, not on the whole document every time.

> Origin: spun out of a 23-chapter physics paper where an AI reviewer noticed
> the term "P&H" was used ~40 times with no definition. The author's reaction —
> *"you can detect an undefined variable even in your own writing"* — became
> this tool.

## Why differential matters

Re-reading a whole book to ask "is every term explained?" is expensive whether
a human or an LLM does it. `explain-lint` keeps a **ledger** of each term's
first appearance, keyed by a **hash of that line's text** — not its line
number. So:

- Add a paragraph up front and every line number shifts? **No noise.** The
  hashes still match; `--sync` rewrites the numbers silently.
- Actually *reword* where a term first appears? **That one term** is flagged
  `MOVED` — re-judge it, nothing else.
- A genuinely new term appears? It's flagged `NEW` — judge it once, and it's
  remembered forever.

The cost of the human/LLM judgment collapses from *O(document)* every run to
*O(what you changed)*.

## Install

Pure Python 3, no dependencies.

```
git clone <this repo>
python explain_lint.py your_doc.md
```

## Quick start

```bash
# 1. See every term's first occurrence (seed material for a ledger)
python explain_lint.py doc.md --dump

# 2. Build doc.md.terms.md (the ledger) — judge each term's category/explained
#    (by hand, or hand the NEW list to an LLM). See format below.

# 3. From now on, this is all you run. It stays silent until something changes:
python explain_lint.py doc.md          # exit 0 = nothing new; exit 1 = NEW/MOVED

# After edits that only shift line numbers:
python explain_lint.py doc.md --sync   # rewrite line numbers for unchanged terms
```

Multiple files are read in order (useful for a book split into chapters):

```bash
python explain_lint.py ch01.md ch02.md ch03.md --ledger book.terms.md
```

## The ledger

A plain Markdown table you (or an LLM) edit. The tool maintains the first four
columns mechanically; you own `explained` and `notes`.

```
| term | category | first_seen | hash | explained | notes |
|---|---|---|---|---|---|
| ホロノミー | needs-explanation | ch12.md:42 §Geometry | ab12cd34 | no  | GAP: used with no gloss |
| Markov     | needs-explanation | ch01.md:5  §Intro    | 50632610 | yes | glossed inline on first use |
| Introduction | exclude         | ch01.md:3  §Intro    | d69dd448 | na  | heading word |
```

Suggested vocabularies (not enforced — they are just strings):

- `category`: `needs-explanation` / `common` / `proper-noun` / `exclude`
- `explained`: `yes` / `no` / `na`

**The actionable output is `explained = no`** — terms that need a gloss and
don't have one. Grep them straight out of the ledger:

```bash
grep '| no |' doc.md.terms.md
```

## What it does — and doesn't

**Does (the machine-detection core):**

- Extract candidate terms: katakana runs (`--min-kana`, default 3) and/or Latin
  words. Toggle with `--no-kana` / `--no-latin`.
- Record each term's first occurrence: file, line, nearest heading, line-hash.
- Ignore fenced code, inline code, `$math$`, `$$math$$`, image tags, and URLs.
- Diff against the ledger → `NEW` / `MOVED` / `GONE`; exit 1 on NEW or MOVED.

**Does not (on purpose):**

- Decide whether a term is explained. That verdict is a separate human/LLM
  layer written into the ledger. The tool only keeps the ledger honest against
  the text and tells you what is new to judge. This keeps the core deterministic,
  offline, dependency-free, and auditable; the (fuzzy, model-dependent) judgment
  stays a pluggable step you control.

## Roadmap

This is the MVP — the deterministic core. Envisioned next:

- An optional judgment plugin (LLM API) that fills `category` / `explained` for
  the `NEW` list automatically.
- Richer term extraction (multi-word phrases; language packs beyond kana+Latin).
- A CI action (fail a PR when a new unexplained term lands in docs).
- An editor integration (flag the gap as you write).

## License

MIT — see [LICENSE](LICENSE).
