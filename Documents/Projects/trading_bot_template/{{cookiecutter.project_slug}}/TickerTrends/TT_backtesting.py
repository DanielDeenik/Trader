import backtrader as bt
import numpy as np
from strategy import TrendingStrategy

def backtest_model(model, X_test, y_test):
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=X_test))
    cerebro.addstrategy(TrendingStrategy, model=model)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio)
    cerebro.addanalyzer(bt.analyzers.Returns)
    results = cerebro.run()
    sharpe_ratio = results[0].analyzers.sharperatio.get_analysis().get("sharperatio", None)
    returns = results[0].analyzers.returns.get_analysis().get("rtot", None)
    print(f"Backtest Sharpe Ratio: {sharpe_ratio}")
    print(f"Backtest Returns: {returns}")

    predictions = model.predict(X_test)
    accuracy = np.mean(np.round(predictions) == y_test)
    print(f"Model Accuracy: {accuracy}")
