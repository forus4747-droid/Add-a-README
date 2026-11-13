# trading-lab — tested trading toolkit and final skill

Built by testing 20 popular open-source trading repositories on 2016–2025 US stock data, keeping what
proved correct, fixing or dropping what did not. Start with `reports/00_INDEX.md`.

| Folder | What it is |
|---|---|
| `protocol/` | The frozen test rules: data splits, no-peeking rule, strategies, worker rulebooks |
| `reports/` | One report per step and per repo; `03_00_STEP3_SUMMARY.md` is the one-page result |
| `lab/` | Data loading and the fixed scoring harness |
| `reference/`, `tests/` | Independent reference backtester and its hand-checked tests |
| `adapters/` | Each engine running the same two strategies; `scripts/compare_trades.py` checks them |
| `skills/` | Each repo's prediction method, run without look-ahead |
| `final/` | The final skill (`skill.py`) and how it was selected |
| `scripts/` | Data fetch, audit, repair, scoring |
| `results/` | Raw outputs behind every number in the reports |

Data is not stored here (too large); `scripts/fetch_data.py`, `scripts/fetch_daily.py` and
`scripts/repair_daily.py` rebuild it from Alpaca, and `reports/01_data_manifest.csv` holds file hashes.
Environment: `scripts/setup-trading-stack.sh`.

**Honest headline:** the engines can be made exact; none of the public prediction recipes showed an edge on unseen data; the final skill ranked in the right direction in 11 of 11 years but is far too small to trade, and did not pass the sealed 2026 test (`reports/05_sealed_test.md`).
on unseen data; the final skill is consistent in direction but too small to be called a proven edge.
Nothing here is financial advice.
