#!/usr/bin/env bash
# Trading stack: each tool in its own uv venv under $ROOT/envs, source repos under $ROOT/repos.
# Idempotent; never fails the session start.
ROOT=${TRADING_ROOT:-/home/user/trading-stack}
mkdir -p "$ROOT/envs" "$ROOT/repos" "$ROOT/logs"
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null || pip install -q uv
mk() { local n=$1 py=$2; shift 2; [ -f "$ROOT/envs/$n/.ok" ] && return; rm -rf "$ROOT/envs/$n"
  { uv venv -q --python "$py" "$ROOT/envs/$n" && VIRTUAL_ENV="$ROOT/envs/$n" uv pip install "$@" && touch "$ROOT/envs/$n/.ok"; } \
    >"$ROOT/logs/$n.log" 2>&1 || echo "trading-stack: $n failed"; }
cl() { local d="$ROOT/repos/$(basename $1)"; [ -d "$d" ] || git clone -q --depth 1 "https://github.com/$1" "$d"; }
for r in hummingbot/hummingbot stefan-jansen/machine-learning-for-trading TauricResearch/TradingAgents virattt/ai-hedge-fund; do cl $r || true; done
mk core 3.12 ccxt alpaca-py ib_async yfinance "TA-Lib>=0.6" pandas-ta backtesting backtrader vectorbt "plotly<6" &
mk nautilus 3.12 nautilus_trader &
mk freqtrade 3.12 freqtrade &
mk lean 3.12 lean &
wait
mk jesse 3.12 jesse &
mk vnpy 3.12 vnpy &
mk octobot 3.10 OctoBot &
mk openbb 3.12 openbb &
wait
mk qlib 3.11 pyqlib &
mk zipline 3.11 zipline-reloaded pyfolio-reloaded &
mk tradingagents 3.12 -e "$ROOT/repos/TradingAgents" &
mk ai-hedge-fund 3.12 -e "$ROOT/repos/ai-hedge-fund" &
wait
mk finrl 3.11 finrl gymnasium matplotlib pandas stable-baselines3 alpaca-trade-api exchange-calendars pytz stockstats wrds yfinance
exit 0
