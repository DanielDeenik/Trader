import pandas as pd

# Example: Breakout Setup
def breakout_signal(data, window=20):
    rolling_high = data['Close'].rolling(window=window).max()
    signal = (data['Close'] > rolling_high.shift(1))  # Breakout condition
    return signal.astype(int)  # Returns 1 for breakout, 0 otherwise
