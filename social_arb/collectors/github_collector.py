"""GitHub activity collector for engineering velocity signals."""

import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

# Organization mapping: symbol -> GitHub org name
ORG_MAP = {
    "DATABRICKS": "databricks",
    "STRIPE": "stripe",
    "ANDURIL": "anduril",
    "ANTHROPIC": "anthropics",
    "COREWEAVE": "coreweave",
    "PALANTIR": "palantir",
    "PLTR": "palantir",
    "HASHICORP": "hashicorp",
    "DATADOG": "DataDog",
    "DDOG": "DataDog",
}

# Public companies (by ticker)
PUBLIC_COMPANIES = {"PLTR", "DDOG"}


class GitHubCollector(BaseCollector):
    """Collects GitHub activity for private companies as engineering velocity proxy."""

    def __init__(self):
        self.api_base = "https://api.github.com"
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "User-Agent": "Social-Arb-Collector/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    @property
    def source_name(self) -> str:
        return "github"

    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        """Collect GitHub activity for given symbols (company names)."""
        signals = []
        errors = []
        scanned = []

        for symbol in symbols:
            org_name = ORG_MAP.get(symbol.upper())
            if not org_name:
                errors.append(f"{symbol}: not found in ORG_MAP")
                logger.warning(f"[github] {symbol}: not in ORG_MAP")
                continue

            try:
                # Determine if public or private company
                is_public = symbol.upper() in PUBLIC_COMPANIES

                # Collect org repos
                repos_data = self._get_org_repos(org_name)
                if not repos_data:
                    errors.append(f"{symbol}: no public repos found")
                    logger.warning(f"[github] {symbol}: no repos")
                    continue

                scanned.append(symbol)

                # Aggregate metrics
                total_stars = 0
                total_forks = 0
                total_open_issues = 0
                recent_pushes = 0
                all_languages = {}
                repo_count = 0

                for repo in repos_data:
                    if repo.get("fork"):
                        continue  # Skip forked repos

                    repo_count += 1
                    total_stars += repo.get("stargazers_count", 0)
                    total_forks += repo.get("forks_count", 0)
                    total_open_issues += repo.get("open_issues_count", 0)

                    # Count recent pushes (last 7 days)
                    recent_pushes += self._count_recent_pushes(org_name, repo["name"])

                    # Aggregate languages
                    languages = self._get_languages(org_name, repo["name"])
                    for lang, count in languages.items():
                        all_languages[lang] = all_languages.get(lang, 0) + count

                if repo_count == 0:
                    errors.append(f"{symbol}: no non-forked repos found")
                    continue

                # Calculate activity strength
                activity_score = total_stars + (total_forks * 2) + recent_pushes
                # Normalize: assume 5000 is a strong signal
                strength = min(1.0, activity_score / 5000.0)

                # Determine direction
                direction = "bullish" if strength > 0.3 else "neutral" if strength > 0.1 else "bearish"

                # Top languages
                top_languages = sorted(
                    all_languages.items(), key=lambda x: x[1], reverse=True
                )[:5]

                signal = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "source": "github",
                    "signal_type": "github_activity",
                    "direction": direction,
                    "strength": strength,
                    "confidence": 0.8,
                    "data_class": "public" if is_public else "private",
                    "raw": {
                        "org": org_name,
                        "stars": total_stars,
                        "forks": total_forks,
                        "open_issues": total_open_issues,
                        "recent_pushes": recent_pushes,
                        "repo_count": repo_count,
                        "top_languages": top_languages,
                    },
                }

                signals.append(signal)
                logger.info(
                    f"[github] {symbol}: {repo_count} repos, "
                    f"{total_stars} stars, {recent_pushes} recent pushes"
                )

            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[github] {symbol} failed: {e}")

        return CollectorResult(
            source="github",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )

    def _get_org_repos(self, org_name: str) -> List[Dict[str, Any]]:
        """Fetch all public repos for an organization."""
        try:
            url = f"{self.api_base}/orgs/{org_name}/repos"
            params = {"type": "public", "per_page": 100}

            repos = []
            page = 1
            while True:
                params["page"] = page
                response = requests.get(
                    url, headers=self.headers, params=params, timeout=10
                )
                response.raise_for_status()

                data = response.json()
                if not data:
                    break

                repos.extend(data)
                page += 1

                # Limit to avoid excessive rate limiting
                if page > 3:
                    break

            return repos
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch repos for {org_name}: {e}")
            return []

    def _count_recent_pushes(self, org_name: str, repo_name: str) -> int:
        """Count push events in the last 7 days."""
        try:
            url = f"{self.api_base}/repos/{org_name}/{repo_name}/events"
            params = {"per_page": 100}

            response = requests.get(
                url, headers=self.headers, params=params, timeout=10
            )
            response.raise_for_status()

            events = response.json()
            now = datetime.utcnow()
            cutoff = now - timedelta(days=7)

            push_count = 0
            for event in events:
                if event.get("type") == "PushEvent":
                    event_time = datetime.fromisoformat(
                        event["created_at"].replace("Z", "+00:00")
                    )
                    if event_time > cutoff:
                        push_count += 1

            return push_count
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch events for {org_name}/{repo_name}: {e}")
            return 0

    def _get_languages(self, org_name: str, repo_name: str) -> Dict[str, int]:
        """Get language distribution for a repository."""
        try:
            url = f"{self.api_base}/repos/{org_name}/{repo_name}/languages"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json() or {}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch languages for {org_name}/{repo_name}: {e}")
            return {}
