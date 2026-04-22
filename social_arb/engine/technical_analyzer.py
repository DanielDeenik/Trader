"""
Technical Analysis Engine

Pure Python technical indicator calculations for OHLCV data.
No external dependencies beyond standard library + math.

All functions accept lists of dicts with keys: date, open, high, low, close, volume
Returns lists of dicts with original keys plus indicator values.
"""

import math
from typing import List, Dict, Optional, Tuple


def sma(ohlcv_data: List[Dict], period: int = 20, key: str = "close") -> List[Dict]:
    """
    Simple Moving Average.

    Args:
        ohlcv_data: List of OHLCV bars
        period: SMA period (default 20)
        key: Which price to average (default "close")

    Returns:
        List with SMA values in each bar dict under key "sma_{period}"
    """
    result = []
    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()

        if i < period - 1:
            bar_copy[f"sma_{period}"] = None
        else:
            window = [ohlcv_data[j].get(key, 0) for j in range(i - period + 1, i + 1)]
            bar_copy[f"sma_{period}"] = sum(window) / period

        result.append(bar_copy)

    return result


def ema(ohlcv_data: List[Dict], period: int = 20, key: str = "close") -> List[Dict]:
    """
    Exponential Moving Average.

    Args:
        ohlcv_data: List of OHLCV bars
        period: EMA period (default 20)
        key: Which price to average (default "close")

    Returns:
        List with EMA values in each bar dict under key "ema_{period}"
    """
    result = []
    multiplier = 2 / (period + 1)

    ema_val = None

    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()
        price = bar.get(key, 0)

        if i < period - 1:
            bar_copy[f"ema_{period}"] = None
        else:
            if ema_val is None:
                # Initialize with SMA on first calculation
                ema_val = sum([ohlcv_data[j].get(key, 0) for j in range(i - period + 1, i + 1)]) / period
            else:
                ema_val = price * multiplier + ema_val * (1 - multiplier)

            bar_copy[f"ema_{period}"] = ema_val

        result.append(bar_copy)

    return result


def rsi(ohlcv_data: List[Dict], period: int = 14, key: str = "close") -> List[Dict]:
    """
    Relative Strength Index.

    Args:
        ohlcv_data: List of OHLCV bars
        period: RSI period (default 14)
        key: Which price to use (default "close")

    Returns:
        List with RSI values (0-100) under key "rsi_{period}"
    """
    result = []

    gains = []
    losses = []

    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()

        if i == 0:
            bar_copy[f"rsi_{period}"] = None
            result.append(bar_copy)
            continue

        price = bar.get(key, 0)
        prev_price = ohlcv_data[i - 1].get(key, 0)
        change = price - prev_price

        gains.append(max(0, change))
        losses.append(max(0, -change))

        if i < period:
            bar_copy[f"rsi_{period}"] = None
        else:
            # Calculate average gains and losses
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period

            if avg_loss == 0:
                rsi_val = 100 if avg_gain > 0 else 50
            else:
                rs = avg_gain / avg_loss
                rsi_val = 100 - (100 / (1 + rs))

            bar_copy[f"rsi_{period}"] = rsi_val

        result.append(bar_copy)

    return result


def macd(ohlcv_data: List[Dict], fast: int = 12, slow: int = 26, signal: int = 9,
         key: str = "close") -> List[Dict]:
    """
    MACD (Moving Average Convergence Divergence).

    Returns:
        List with MACD line, signal line, and histogram under keys:
        - macd_line
        - macd_signal
        - macd_histogram
    """
    # Calculate EMAs
    fast_ema_data = ema(ohlcv_data, fast, key)
    slow_ema_data = ema(ohlcv_data, slow, key)

    result = []
    macd_line_values = []

    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()

        fast_val = fast_ema_data[i].get(f"ema_{fast}")
        slow_val = slow_ema_data[i].get(f"ema_{slow}")

        if fast_val is None or slow_val is None:
            bar_copy["macd_line"] = None
            bar_copy["macd_signal"] = None
            bar_copy["macd_histogram"] = None
        else:
            macd_val = fast_val - slow_val
            macd_line_values.append(macd_val)
            bar_copy["macd_line"] = macd_val

            # Calculate signal line (EMA of MACD)
            if len(macd_line_values) < signal:
                bar_copy["macd_signal"] = None
                bar_copy["macd_histogram"] = None
            else:
                # Simple signal line calculation
                signal_val = sum(macd_line_values[-signal:]) / signal
                bar_copy["macd_signal"] = signal_val
                bar_copy["macd_histogram"] = macd_val - signal_val

        result.append(bar_copy)

    return result


def bollinger_bands(ohlcv_data: List[Dict], period: int = 20, std_dev: float = 2.0,
                   key: str = "close") -> List[Dict]:
    """
    Bollinger Bands.

    Args:
        period: BBand period (default 20)
        std_dev: Standard deviations (default 2.0)

    Returns:
        List with upper, middle, lower bands and width under keys:
        - bb_upper, bb_middle, bb_lower, bb_width
    """
    result = []

    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()

        if i < period - 1:
            bar_copy["bb_upper"] = None
            bar_copy["bb_middle"] = None
            bar_copy["bb_lower"] = None
            bar_copy["bb_width"] = None
        else:
            window = [ohlcv_data[j].get(key, 0) for j in range(i - period + 1, i + 1)]

            middle = sum(window) / period
            variance = sum((x - middle) ** 2 for x in window) / period
            std = math.sqrt(variance)

            upper = middle + (std_dev * std)
            lower = middle - (std_dev * std)
            width = upper - lower

            bar_copy["bb_middle"] = middle
            bar_copy["bb_upper"] = upper
            bar_copy["bb_lower"] = lower
            bar_copy["bb_width"] = width

        result.append(bar_copy)

    return result


def atr(ohlcv_data: List[Dict], period: int = 14) -> List[Dict]:
    """
    Average True Range.

    True Range = max(high - low, abs(high - close[prev]), abs(low - close[prev]))
    ATR = EMA of True Range

    Returns:
        List with ATR values under key "atr_{period}"
    """
    result = []
    true_ranges = []

    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()

        high = bar.get("high", 0)
        low = bar.get("low", 0)
        close = bar.get("close", 0)

        if i == 0:
            tr = high - low
        else:
            prev_close = ohlcv_data[i - 1].get("close", 0)
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )

        true_ranges.append(tr)

        if i < period - 1:
            bar_copy[f"atr_{period}"] = None
        else:
            # EMA of true ranges
            if i == period - 1:
                atr_val = sum(true_ranges) / period
            else:
                prev_atr = result[i - 1].get(f"atr_{period}", 0)
                atr_val = (prev_atr * (period - 1) + tr) / period

            bar_copy[f"atr_{period}"] = atr_val

        result.append(bar_copy)

    return result


def momentum(ohlcv_data: List[Dict], period: int = 10, key: str = "close") -> List[Dict]:
    """
    Momentum indicator (rate of change).

    Momentum = ((Close - Close[period periods ago]) / Close[period periods ago]) * 100

    Returns:
        List with momentum values (%) under key "momentum_{period}"
    """
    result = []

    for i, bar in enumerate(ohlcv_data):
        bar_copy = bar.copy()

        if i < period:
            bar_copy[f"momentum_{period}"] = None
        else:
            current = bar.get(key, 0)
            past = ohlcv_data[i - period].get(key, 0)

            if past == 0:
                momentum_val = 0
            else:
                momentum_val = ((current - past) / past) * 100

            bar_copy[f"momentum_{period}"] = momentum_val

        result.append(bar_copy)

    return result


def calculate_all_indicators(ohlcv_data: List[Dict]) -> List[Dict]:
    """
    Calculate all standard technical indicators.

    Returns OHLCV data enriched with:
    - SMA 20, 50
    - EMA 12, 26
    - RSI 14
    - MACD (12, 26, 9)
    - Bollinger Bands (20, 2.0)
    - ATR 14
    - Momentum 10
    """
    result = ohlcv_data.copy()

    result = sma(result, 20)
    result = sma(result, 50)
    result = ema(result, 12)
    result = ema(result, 26)
    result = rsi(result, 14)
    result = macd(result)
    result = bollinger_bands(result)
    result = atr(result)
    result = momentum(result)

    return result
