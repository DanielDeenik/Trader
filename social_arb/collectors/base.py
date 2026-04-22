"""Base collector interface for all data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CollectorResult:
    """Output of a collection run."""
    source: str
    signals: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    symbols_scanned: List[str] = field(default_factory=list)

    @property
    def signal_count(self) -> int:
        return len(self.signals)


class BaseCollector(ABC):
    """Abstract base for all data collectors. No demo mode — real data or error."""

    @abstractmethod
    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @property
    def data_class(self) -> str:
        return "public"
