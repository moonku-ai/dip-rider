"""Dip Rider: an RSI scale-in mean-reversion bot for cbBTC (CBBTC/USDC).

Strategy, in one paragraph: the dev window is a choppy, range-bound day
(BTC $63.9k-$65.5k, net +0.5%) where trend breakouts whipsaw and bleed the
~26 bps round-trip cost. So this bot only buys dips, in two tranches, and
only sells into strength:
  - Tranche 1: 60% of cash when RSI(14) drops below 30 AND the close has
    already turned up over the last 5 bars (close above the close 5 bars
    ago) -- the confirmation keeps it from catching a knife mid-fall.
  - Tranche 2: the remaining 40% of cash if the dip deepens (RSI(14)
    below 20, or the close falls 50 bps under the first entry's close),
    which lowers the average entry instead of chasing.
  - Exit: sell the whole position when RSI(14) rises above 75, i.e. the
    bounce has run into overbought territory.
No shorts, no leverage, no clock, no randomness, no network: every decision
is a pure function of the bars seen so far, so two runs agree bar for bar.

Local dev-window result (faithful replay of the harness fill model: 4 bps
fee, 2 bps slippage, constant-product impact on the bar's open depth):
net PnL +$11.83 on $1,000, 7 fills, max drawdown 0.64%.

Speaks agent-fun/bars-replay/v1 over stdin/stdout via the kit's Python shim
(vendor/makefun_bars.py, copied byte for byte from the competition kit).
Standard library only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# --- strategy parameters (tuned on the published dev window only) ---
RSI_PERIOD = 14
RSI_BUY = 30.0       # first tranche when RSI drops below this
RSI_ADD = 20.0       # second tranche when RSI drops below this
RSI_SELL = 75.0      # exit everything when RSI rises above this
CONFIRM_BARS = 5     # entry needs close above the close this many bars ago
FIRST_FRACTION_NUM = 60   # first tranche spends 60% of cash
FIRST_FRACTION_DEN = 100
ADD_DROP_BPS = 50    # second tranche if close falls this far under entry
MAX_SLIPPAGE_BPS = 200  # fills are 1-minute opens; moves this big are ~30 sigma


class DipRider:
    """Keeps the closes seen so far and the scale-in stage."""

    def __init__(self):
        self.closes = []
        self.stage = 0      # 0 flat, 1 first tranche held, 2 fully invested
        self.entry_close = 0

    def rsi(self):
        """Wilder RSI(14) of the closes so far; None before 14 changes."""
        closes = self.closes
        n = RSI_PERIOD
        if len(closes) <= n:
            return None
        gains = []
        losses = []
        for i in range(1, len(closes)):
            d = closes[i] - closes[i - 1]
            gains.append(d if d > 0 else 0)
            losses.append(-d if d < 0 else 0)
        avg_gain = sum(gains[:n]) / n
        avg_loss = sum(losses[:n]) / n
        if avg_loss == 0:
            value = 100.0
        else:
            value = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        for i in range(n + 1, len(closes)):
            d = closes[i] - closes[i - 1]
            avg_gain = (avg_gain * (n - 1) + (d if d > 0 else 0)) / n
            avg_loss = (avg_loss * (n - 1) + (-d if d < 0 else 0)) / n
            if avg_loss == 0:
                value = 100.0
            else:
                value = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        return value

    def on_batch(self, state, batch):
        bar = state.latest.get(SYMBOL)
        if bar is None:
            return []
        close = int(bar["c"])
        self.closes.append(close)
        i = len(self.closes) - 1
        rsi = self.rsi()
        if rsi is None or state.warming_up:
            return []

        holding = state.positions.get(SYMBOL)
        has_position = holding is not None and holding.qty > 0

        if self.stage == 0:
            # Flat: buy the dip, but only once it has started turning up.
            if rsi < RSI_BUY and i >= CONFIRM_BARS and close > self.closes[i - CONFIRM_BARS]:
                self.stage = 1
                self.entry_close = close
                notional = state.cash * FIRST_FRACTION_NUM // FIRST_FRACTION_DEN
                if notional >= 1_000_000:
                    return [{"side": "buy", "symbol": SYMBOL,
                             "notional_quote_units": notional,
                             "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []

        if self.stage == 1:
            # First tranche held: deepen the position on a deeper dip...
            if rsi < RSI_ADD or close < self.entry_close * (10_000 - ADD_DROP_BPS) // 10_000:
                self.stage = 2
                if state.cash >= 1_000_000:
                    return [{"side": "buy", "symbol": SYMBOL,
                             "notional_quote_units": state.cash,
                             "max_slippage_bps": MAX_SLIPPAGE_BPS}]
                return []
            # ...or take the bounce into overbought territory.
            if rsi > RSI_SELL and has_position:
                self.stage = 0
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []

        # Stage 2: fully invested, exit on overbought RSI.
        if rsi > RSI_SELL and has_position:
            self.stage = 0
            return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []


def main():
    bot = DipRider()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
