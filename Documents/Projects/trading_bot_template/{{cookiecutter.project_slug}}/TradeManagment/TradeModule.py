import ccxt

# Example API setup for Binance
binance = ccxt.binance({
    'apiKey': 'your_api_key',
    'secret': 'your_secret',
})

def place_order(symbol, side, quantity, order_type="market"):
    try:
        order = binance.create_order(symbol=symbol, type=order_type, side=side, amount=quantity)
        return order
    except Exception as e:
        print(f"Order failed: {e}")
        return None
