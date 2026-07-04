# explain-lint ledger

- Machine-maintained first-occurrence table. `explain_lint.py` diffs the
  text against this file; only NEW/MOVED terms need a fresh judgment.
- Edit `category` / `explained` / `notes` by hand or with an LLM.
- `first_seen` line numbers are auto-updated by `--sync`.

| term | category | first_seen | hash | explained | notes |
|---|---|---|---|---|---|
| Example | exclude | sample.md:1 §Example: an article with an explanation gap | e09e47e5 | na | heading word |
| Introduction | exclude | sample.md:3 §Introduction | d69dd448 | na | heading |
| Markov | needs-explanation | sample.md:5 §Introduction | 50632610 | yes | glossed inline on first use |
| Each | exclude | sample.md:6 §Introduction | 26d0173e | na | sentence-start false positive |
| Lindblad | needs-explanation | sample.md:7 §Introduction | ebc5a015 | no | GAP: used with no gloss |
| Here | exclude | sample.md:9 §Introduction | 67cb8fbd | na | sentence start |
| That | exclude | sample.md:10 §Introduction | a334820b | na | sentence start |
| Method | exclude | sample.md:13 §Method | e6062d4c | na | heading |
| オブザーバブル | needs-explanation | sample.md:15 §Method | 8339d7a1 | no | GAP: no gloss |
| コヒーレンス | needs-explanation | sample.md:15 §Method | 8339d7a1 | no | GAP: no gloss |
| The | exclude | sample.md:15 §Method | 8339d7a1 | na | article |
| Fourier | needs-explanation | sample.md:16 §Method | 6f3a5e5e | no | GAP: no gloss |
| LLM | common | sample.md:19 §Method | 207c0b64 | na | assumed known for audience |
