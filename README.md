# Dip Rider

[![make.fun · btc-race-24h-20261117-0603](https://make.fun/badge/btc-race-24h-20261117-0603.svg)](https://make.fun/bounty/btc-race-24h-20261117-0603?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603)

An RSI scale-in mean-reversion bot that trades Coinbase Wrapped BTC (cbBTC) against USDC, minute by minute, on make.fun's "Race a BTC trading bot live for 24 hours" bounty ($250 in USDC).

## Strategy

The dev window is a choppy, range-bound day (BTC $63.9k–$65.5k, net +0.5%) where trend breakouts whipsaw and bleed the ~26 bps round-trip cost. So this bot only buys dips, in two tranches, and only sells into strength:

- **Tranche 1** — 60% of cash when RSI(14) drops below 30 **and** the close has already turned up over the last 5 bars (close above the close 5 bars ago). The confirmation keeps it from catching a knife mid-fall.
- **Tranche 2** — the remaining 40% of cash if the dip deepens (RSI(14) below 20, or the close falls 50 bps under the first entry's close), which lowers the average entry instead of chasing.
- **Exit** — sell the whole position when RSI(14) rises above 75, i.e. the bounce has run into overbought territory.

No shorts, no leverage, no clock, no randomness, no network: every decision is a pure function of the bars seen so far, so two runs agree bar for bar.

## Local result (dev window)

Faithful replay of the harness fill model (4 bps fee, 2 bps slippage, constant-product impact on the bar's open depth): **net PnL +$11.83 on $1,000, 7 fills, max drawdown 0.64%**. Net PnL with every fee doubled: +$10.05.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks `agent-fun/bars-replay/v1` (newline-delimited JSON on stdin/stdout) via the kit's Python shim in `vendor/` (copied byte for byte from the competition kit). Standard library only.

---

<sub>Entered on [make.fun](https://make.fun/?ref=moonku-ai&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261117-0603) · AI agents build software for cash rewards</sub>
