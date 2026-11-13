# Fixed benchmark strategies for the engine accuracy test (E)

Long-only, one position per symbol, each symbol independent.
Size: `shares = floor(10000 / fill_price)`. Cost: 0.05% of traded value per side.

## S1 — Opening-range breakout (5-min bars)
1. Opening range = highest high and lowest low of the six bars 09:30–09:55.
2. From the 10:00 bar through the 15:40 bar: if flat, no trade yet today, and bar close > range high → buy at next bar's open.
3. If long and bar close < range low → sell at next bar's open.
4. If still long, sell at the open of the 15:55 bar.
5. At most one trade per symbol per day. Days with fewer than 78 bars are skipped.

## S2 — 20/50-day SMA cross (daily bars built from the 5-min bars)
1. Daily bar: open = first open, high = max, low = min, close = last close, volume = sum.
2. If flat and SMA20 > SMA50 at day t's close and SMA20 <= SMA50 at day t-1's close → buy at day t+1's open.
3. If long and SMA20 < SMA50 at day t's close → sell at day t+1's open.
4. Positions open at the end of the window are closed at the last day's close.
