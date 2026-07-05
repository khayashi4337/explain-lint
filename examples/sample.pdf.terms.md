# explain-lint ledger

- Machine-maintained first-occurrence table. explain-lint diffs the text
  against this file; only NEW/MOVED terms need a fresh judgment.
- Edit `category` / `explained` / `notes` by hand or with an LLM.
- `first_seen` line numbers are auto-updated by `--sync`.

| term | category | first_seen | hash | explained | notes |
|---|---|---|---|---|---|
| Markov | needs-explanation | sample.pdf:p1 | 1b3f44b3 | yes | glossed inline |
| Lindblad | needs-explanation | sample.pdf:p1 | ebc5a015 | no | GAP: no gloss |
| Fourier | needs-explanation | sample.pdf:p1 | 6f3a5e5e | no | GAP: no gloss |
