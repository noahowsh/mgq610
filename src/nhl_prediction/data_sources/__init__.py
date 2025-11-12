"""Unified accessors for official NHL data sources."""

from .gamecenter import GamecenterClient  # noqa: F401
from .legacy_api import LegacyStatsClient  # noqa: F401
from .stats_rest import StatsRestClient  # noqa: F401

__all__ = ["GamecenterClient", "StatsRestClient", "LegacyStatsClient"]
