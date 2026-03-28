import pytest
from social_arb.collectors.base import BaseCollector, CollectorResult


class TestBaseCollector:
    def test_result_dataclass(self):
        result = CollectorResult(source="test", signals=[], errors=[], symbols_scanned=["NVDA"])
        assert result.source == "test"
        assert result.signal_count == 0

    def test_abstract_collect_raises(self):
        with pytest.raises(TypeError):
            BaseCollector()


class TestYFinanceCollector:
    def test_collect_single_symbol(self):
        from social_arb.collectors.yfinance_collector import YFinanceCollector
        collector = YFinanceCollector()
        result = collector.collect(symbols=["AAPL"], period="5d")
        assert result.source == "yfinance"
        assert result.signal_count > 0
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert "symbol" in signal
            assert "source" in signal

    def test_collect_returns_ohlcv(self):
        from social_arb.collectors.yfinance_collector import YFinanceCollector
        collector = YFinanceCollector()
        result = collector.collect(symbols=["AAPL"], period="5d")
        ohlcv_signals = [s for s in result.signals if s.get("signal_type") == "ohlcv"]
        assert len(ohlcv_signals) > 0
        bar = ohlcv_signals[0]
        for field in ["open", "high", "low", "close", "volume"]:
            assert field in bar, f"Missing field: {field}"

    def test_invalid_symbol_returns_error(self):
        from social_arb.collectors.yfinance_collector import YFinanceCollector
        collector = YFinanceCollector()
        result = collector.collect(symbols=["ZZZZZZNOTREAL"], period="5d")
        assert len(result.errors) > 0 or result.signal_count == 0


class TestRedditCollector:
    def test_collect_structure(self):
        from social_arb.collectors.reddit_collector import RedditCollector
        collector = RedditCollector()
        assert collector.source_name == "reddit"

    def test_collect_returns_result(self):
        from social_arb.collectors.reddit_collector import RedditCollector
        collector = RedditCollector()
        # Use common symbols that are likely mentioned
        result = collector.collect(
            symbols=["NVDA", "TSLA", "AAPL"],
            subreddits=["stocks"],
            limit=10,
        )
        assert result.source == "reddit"
        assert isinstance(result.signals, list)
        assert isinstance(result.errors, list)
        # All signals should be public
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert signal["source"] == "reddit"
            assert signal["signal_type"] == "social_mention"


class TestTrendsCollector:
    def test_collector_structure(self):
        from social_arb.collectors.trends_collector import TrendsCollector
        collector = TrendsCollector()
        assert collector.source_name == "google_trends"

    def test_collect_returns_result(self):
        from social_arb.collectors.trends_collector import TrendsCollector
        collector = TrendsCollector()
        result = collector.collect(symbols=["NVDA"])
        assert result.source == "google_trends"
        for signal in result.signals:
            assert signal["data_class"] == "public"


class TestSECEdgarCollector:
    def test_collector_structure(self):
        from social_arb.collectors.sec_edgar_collector import SECEdgarCollector
        collector = SECEdgarCollector()
        assert collector.source_name == "sec_edgar"

    def test_collect_nvda(self):
        from social_arb.collectors.sec_edgar_collector import SECEdgarCollector
        collector = SECEdgarCollector()
        result = collector.collect(symbols=["NVDA"])
        assert result.source == "sec_edgar"
        assert result.signal_count > 0
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert signal["source"] == "sec_edgar"
            assert "filing_" in signal["signal_type"]

    def test_unknown_symbol_returns_error(self):
        from social_arb.collectors.sec_edgar_collector import SECEdgarCollector
        collector = SECEdgarCollector()
        result = collector.collect(symbols=["ZZZZNOTREAL"])
        assert len(result.errors) > 0


class TestGitHubCollector:
    def test_collector_structure(self):
        from social_arb.collectors.github_collector import GitHubCollector
        collector = GitHubCollector()
        assert collector.source_name == "github"

    def test_collect_returns_result(self):
        from social_arb.collectors.github_collector import GitHubCollector
        collector = GitHubCollector()
        result = collector.collect(symbols=["STRIPE"])
        assert result.source == "github"
        for signal in result.signals:
            assert signal["data_class"] in ("public", "private")
            assert signal["source"] == "github"

    def test_collect_databricks(self):
        from social_arb.collectors.github_collector import GitHubCollector
        collector = GitHubCollector()
        result = collector.collect(symbols=["DATABRICKS"])
        assert result.source == "github"
        # Either we get signals or we get a rate limit error
        if result.signal_count > 0:
            for signal in result.signals:
                assert signal["source"] == "github"
                assert signal["signal_type"] == "github_activity"
                assert signal["data_class"] == "private"
                assert "raw" in signal
                assert "stars" in signal["raw"]
                assert "forks" in signal["raw"]
                assert "recent_pushes" in signal["raw"]
        else:
            # Rate limit or network error
            assert len(result.errors) > 0

    def test_public_company_classifier(self):
        from social_arb.collectors.github_collector import GitHubCollector
        collector = GitHubCollector()
        # PLTR is public
        result = collector.collect(symbols=["PLTR"])
        if result.signal_count > 0:
            for signal in result.signals:
                assert signal["data_class"] == "public"

    def test_invalid_symbol_returns_error(self):
        from social_arb.collectors.github_collector import GitHubCollector
        collector = GitHubCollector()
        result = collector.collect(symbols=["NOTAREALSYMBOL"])
        assert len(result.errors) > 0


class TestCoinGeckoCollector:
    def test_collector_structure(self):
        from social_arb.collectors.coingecko_collector import CoinGeckoCollector
        collector = CoinGeckoCollector()
        assert collector.source_name == "coingecko"

    def test_collect_returns_result(self):
        from social_arb.collectors.coingecko_collector import CoinGeckoCollector
        collector = CoinGeckoCollector()
        result = collector.collect(symbols=["BTC", "ETH"])
        assert result.source == "coingecko"
        # Validate structure even if no signals due to rate limiting
        assert isinstance(result.signals, list)
        assert isinstance(result.errors, list)
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert signal["source"] == "coingecko"
            assert signal["signal_type"] in ("price_action", "volume_spike", "market_cap_change", "ohlcv")
            assert "raw" in signal
            assert len(signal["raw"]) > 0  # raw dict has data

    def test_collect_single_token(self):
        from social_arb.collectors.coingecko_collector import CoinGeckoCollector
        collector = CoinGeckoCollector()
        result = collector.collect(symbols=["BTC"])
        assert result.source == "coingecko"
        # Either we get signals or we get an error (e.g., rate limit)
        assert result.signal_count > 0 or len(result.errors) > 0
        if result.signal_count > 0:
            signal = result.signals[0]
            assert signal["symbol"] == "BTC"
            assert signal["confidence"] == 0.85
            assert "market_cap_rank" in signal["raw"]

    def test_invalid_token_returns_error(self):
        from social_arb.collectors.coingecko_collector import CoinGeckoCollector
        collector = CoinGeckoCollector()
        result = collector.collect(symbols=["INVALIDTOKEN123"])
        assert len(result.errors) > 0


class TestDeFiLlamaCollector:
    def test_collector_structure(self):
        from social_arb.collectors.defillama_collector import DeFiLlamaCollector
        collector = DeFiLlamaCollector()
        assert collector.source_name == "defillama"

    def test_collect_returns_result(self):
        from social_arb.collectors.defillama_collector import DeFiLlamaCollector
        collector = DeFiLlamaCollector()
        result = collector.collect(symbols=["AAVE", "UNI"])
        assert result.source == "defillama"
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert signal["source"] == "defillama"
            assert signal["signal_type"] == "tvl_metric"
            assert "raw" in signal
            assert "tvl" in signal["raw"]

    def test_collect_single_protocol(self):
        from social_arb.collectors.defillama_collector import DeFiLlamaCollector
        collector = DeFiLlamaCollector()
        result = collector.collect(symbols=["AAVE"])
        assert result.source == "defillama"
        assert result.signal_count > 0
        signal = result.signals[0]
        assert signal["symbol"] == "AAVE"
        assert signal["confidence"] == 0.8
        assert "chains" in signal["raw"]

    def test_invalid_protocol_returns_error(self):
        from social_arb.collectors.defillama_collector import DeFiLlamaCollector
        collector = DeFiLlamaCollector()
        result = collector.collect(symbols=["INVALIDPROTOCOL123"])
        assert len(result.errors) > 0
