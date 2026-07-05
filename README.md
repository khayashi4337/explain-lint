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
python -m explain_lint your_doc.md
```

## Quick start

```bash
# 1. See every term's first occurrence (seed material for a ledger)
python -m explain_lint doc.md --dump

# 2. Build doc.md.terms.md (the ledger) — judge each term's category/explained
#    (by hand, or hand the NEW list to an LLM). See format below.

# 3. From now on, this is all you run. It stays silent until something changes:
python -m explain_lint doc.md          # exit 0 = nothing new; exit 1 = NEW/MOVED

# After edits that only shift line numbers:
python -m explain_lint doc.md --sync   # rewrite line numbers for unchanged terms
```

Multiple files are read in order (useful for a book split into chapters):

```bash
python -m explain_lint ch01.md ch02.md ch03.md --ledger book.terms.md
```

See `examples/sample.md` (English) and `examples/sample_ja.md` (Japanese) for
working examples with pre-built ledgers. PDF samples are at
`examples/sample.pdf` and `examples/sample_ja.pdf` (requires: `pip install explain-lint[pdf]`).

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
  words and abbreviations like `AT&T` / `R&D` / `Peacock-Hall` (`--min-latin`,
  default 3). Toggle with `--no-kana` / `--no-latin`.
- Record each term's first occurrence: file, line, nearest heading, line-hash.
- Ignore fenced code, inline code, `$math$`, `$$math$$`, image tags, and URLs.
- Diff against the ledger → `NEW` / `MOVED` / `GONE`; exit 1 on NEW or MOVED.
- PDF input support: `pypdf` extracts text per page; page numbers replace line
  numbers in `first_seen` (e.g. `book.pdf:p42 §Geometry`). Requires: `pip install explain-lint[pdf]`.
- Back-of-book index: `--index` generates a sorted term → page/line listing from
  the ledger.
- Morphological analysis: `--morph` extracts kanji/hiragana nouns via Janome.
  Requires: `pip install explain-lint[ja]`.

**Does not (on purpose):**

- Decide whether a term is explained. That verdict is a separate human/LLM
  layer written into the ledger. The tool only keeps the ledger honest against
  the text and tells you what is new to judge. This keeps the core deterministic,
  offline, dependency-free, and auditable; the (fuzzy, model-dependent) judgment
  stays a pluggable step you control.

## Use it from an AI assistant (MCP)

The judgment step *is* an AI task — but a cheap one, because the differential
core hands the assistant only the NEW/MOVED terms, not the whole document. The
included **MCP server** (`explain_lint_mcp.py`) is the seam: connect an
assistant (Claude, etc.) and it can run the whole loop itself.

```
pip install mcp        # the core needs nothing; the server needs this
```

Register it (Claude Code / Claude Desktop `mcpServers` config):

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

Tools the assistant sees:

| tool | purpose |
|---|---|
| `lint_report(paths, ledger)` | the diff: NEW / MOVED / GONE terms |
| `get_term_context(term, paths, window)` | first occurrence + surrounding lines, to judge |
| `record_judgment(ledger, term, category, explained, notes, paths)` | write the verdict back |
| `list_gaps(ledger)` | the finding: terms marked `explained = no` |
| `sync_ledger(paths, ledger)` | refresh line numbers after pure drift |
| `dump_terms(paths)` | every first occurrence (seed a ledger) |

The loop the assistant runs: **`lint_report`** → for each NEW term
**`get_term_context`** → judge → **`record_judgment`** → **`list_gaps`** to
report the unexplained terms to you. The server holds no model and makes no API
calls — the intelligence is whatever client connects to it.

## Roadmap

Done: the deterministic core (CLI + importable functions) and the **MCP server**
that lets an assistant drive the judgment loop. Envisioned next:

- A one-call convenience tool that runs the whole loop server-side when the
  client passes it an LLM callback.
- Richer term extraction (multi-word phrases; language packs beyond kana+Latin).
- A CI action (fail a PR when a new unexplained term lands in docs).
- An editor integration (flag the gap as you write).

## Development

The core has no runtime dependencies; the tests need only `pytest`:

```
pip install pytest
python -m pytest
```

The suite (`tests/`) covers the differential lifecycle (NEW/MOVED/GONE and that
a re-judged MOVED clears), ledger round-tripping through special characters,
term extraction and exclusions, `sync` line-drift vs content change, and that
the CLI survives a non-UTF-8 console. Each is also a regression test for a
specific past bug — see `issues/`.

## License

MIT — see [LICENSE](LICENSE).
