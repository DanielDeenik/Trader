"""Configuration — env vars only, no demo mode."""

import os
from pathlib import Path


class Config:
    def __init__(self):
        db_default = str(Path(__file__).parent / "db" / "social_arb.db")
        self.db_path: str = os.getenv("SOCIAL_ARB_DB", str(Path(db_default).resolve()))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self._db_url: str = os.getenv("DATABASE_URL", "")
        self.api_port: int = int(os.getenv("API_PORT", "8000"))
        self.api_host: str = os.getenv("API_HOST", "0.0.0.0")
        self.cors_origins: list = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
        ).split(",")

        # Default tracked symbols (public)
        self.public_symbols: list = os.getenv(
            "PUBLIC_SYMBOLS",
            "NVDA,PLTR,MSFT,AAPL,AMD,TSLA,SHOP,SQ,DDOG,GOOGL,"
            "META,AMZN,INTC,NFLX,V,MA,COST,CRM,OKTA,ROKU,MELI,ARM,APP,PAY,FDX,UPS",
        ).split(",")

        # Private companies (tracked separately)
        self.private_symbols: list = os.getenv(
            "PRIVATE_SYMBOLS", "DATABRICKS,STRIPE,ANDURIL,COREWEAVE,ANTHROPIC"
        ).split(",")

        # Crypto tokens
        self.crypto_symbols: list = os.getenv(
            "CRYPTO_SYMBOLS", "BTC,ETH,SOL,AVAX,LINK,AAVE,UNI,ARB,OP,MATIC"
        ).split(",")

        # Private company domain mappings
        self.private_company_domains: dict = {
            "databricks": "https://www.databricks.com",
            "stripe": "https://stripe.com",
            "anduril": "https://www.anduril.com",
            "coreweave": "https://www.coreweave.com",
            "anthropic": "https://www.anthropic.com",
        }

        self.private_company_career_urls: dict = {
            "databricks": "https://www.databricks.com/careers/",
            "stripe": "https://stripe.com/jobs/",
            "anduril": "https://www.anduril.com/careers/",
            "coreweave": "https://www.coreweave.com/careers/",
            "anthropic": "https://www.anthropic.com/careers/",
        }

        self.private_company_apps: dict = {
            "databricks": [],
            "stripe": [],
            "anduril": [],
            "coreweave": [],
            "anthropic": ["Claude"],
        }

        # Reddit config
        self.reddit_subreddits: list = os.getenv(
            "REDDIT_SUBREDDITS", "wallstreetbets,stocks,investing,SecurityAnalysis,cryptocurrency,defi,ethereum"
        ).split(",")

    @property
    def db_backend(self) -> str:
        """Detect database backend from DATABASE_URL.

        Returns:
            'postgres' if DATABASE_URL starts with postgres://
            'sqlite' otherwise
        """
        if self._db_url.startswith("postgres://") or self._db_url.startswith("postgresql://"):
            return "postgres"
        return "sqlite"

    @property
    def all_symbols(self) -> list:
        """All symbols across all domains."""
        return self.public_symbols + self.private_symbols + self.crypto_symbols

    def __repr__(self):
        return f"Config(backend={self.db_backend}, db={self.db_path}, public={len(self.public_symbols)}, private={len(self.private_symbols)}, crypto={len(self.crypto_symbols)})"


config = Config()
