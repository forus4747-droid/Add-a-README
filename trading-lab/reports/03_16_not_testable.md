# Step 3.16 — Repos that could not be tested here, and why

| Repo | Status | Reason (evidence) |
|---|---|---|
| QuantConnect/Lean | not testable | The `lean` CLI installs, but `lean --version` fails: it must download from `cdn.quantconnect.com` (blocked by this environment's network rules) and backtests run inside Docker (daemon not running here). |
| TauricResearch/TradingAgents | excluded by protocol | Every signal comes from an LLM. LLMs have 2023–2026 market history in their training data, so a look-back test cannot be made peek-free (PROTOCOL §2). Could only be tested forward in time, on days after the model's knowledge cutoff. |
| virattt/ai-hedge-fund (current v2) | excluded by protocol | Same reason: v2 contains only LLM persona agents. Its last rule-based code (v1) was tested in Step 3.8. |
| ccxt/ccxt | not testable | Crypto exchange APIs (e.g. api.binance.com) are blocked here. Indirectly exercised: Freqtrade's engine test ran on ccxt's market-loading code offline. |
| hummingbot/hummingbot | not testable | Market-making bot: needs live exchange order books; official install is conda/Docker. No historical-prediction component to test. |
| Drakkar-Software/OctoBot | not testable | Installs and imports; its strategies and backtester require crypto exchange data, blocked here. |
| ib-api-reloaded/ib_async | not testable | A connector to Interactive Brokers; needs a running IB Gateway and an IB account. Makes no predictions. |
| alpacahq/alpaca-py | used, partly tested | The data source for everything here. Step 3.15 found its daily bars take the last print rather than the auction price; repaired in Step 3.17. |

None of these is counted as "good" or "bad"; they are recorded as untested.
