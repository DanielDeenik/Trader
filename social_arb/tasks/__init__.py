"""Task queue module for Social Arb.

Provides in-process asyncio task queue for coordinating collection, analysis,
and backfill jobs with DB-backed persistence and retry logic.
"""

from .queue import TaskQueue

__all__ = ["TaskQueue"]
