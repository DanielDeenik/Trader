import backtrader as bt
from backtrader.indicators import MACD, RSI

class TrendingStrategy(bt.Strategy):
    params = (
        ("model", None),
        ("macd_fast", 12),
        ("macd_slow", 26),
        ("macd_signal", 9),
        ("rsi_period", 14),
    )

    def __init__(self):
        self.macd = MACD(self.data.close, fastlen=self.params.macd_fast, slowlen=self.params.macd_slow, signallen=self.params.macd_signal)
        self.rsi = RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        prediction = self.params.model.predict(self.data.close.reshape(1, -1, 1))
        if prediction[0] > 0.5 and self.macd.signal > self.macd.macd and self.rsi < 30:
            self.buy()
        elif prediction[0] <= 0.5 and self.macd.signal < self.macd.macd and self.rsi > 70:
            self.sell()
