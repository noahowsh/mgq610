"""Fallback client for the legacy statsapi.web.nhl.com service."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .cache import JSONCache

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://statsapi.web.nhl.com/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_ROOT = PROJECT_ROOT / "data" / "raw" / "legacy_api"


class LegacyStatsClient:
    """Simple helper to mirror the Web API calls against the legacy service."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        cache: Optional[JSONCache] = None,
        rate_limit_seconds: float = 0.35,
    ):
        self.session = session or requests.Session()
        self.cache = cache or JSONCache(DEFAULT_CACHE_ROOT)
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)
        self._last_request = time.time()

    def _request(
        self,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        cache_path: Optional[Path | str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"

        if use_cache and cache_path is not None:
            cached = self.cache.read(cache_path)
            if cached is not None:
                return cached

        self._rate_limit()
        response = self.session.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()

        if cache_path is not None:
            self.cache.write(cache_path, payload)

        return payload

    def get_schedule(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        team_id: Optional[int] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if team_id:
            params["teamId"] = team_id
        cache_name = f"{start_date or 'all'}_{end_date or 'all'}_{team_id or 'lg'}.json"
        cache_path = Path("schedule") / cache_name
        return self._request("schedule", params=params or None, cache_path=cache_path, use_cache=use_cache)

    def get_game_feed(self, game_pk: int | str, *, use_cache: bool = True) -> Dict[str, Any]:
        cache_path = Path("games") / f"{game_pk}.json"
        endpoint = f"game/{game_pk}/feed/live"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_teams(self, *, season: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
        params = {"season": season} if season else None
        cache_path = Path("teams") / f"{season or 'current'}.json"
        return self._request("teams", params=params, cache_path=cache_path, use_cache=use_cache)

    def get_team_roster(self, team_id: int, season: Optional[str] = None, *, use_cache: bool = True) -> Dict[str, Any]:
        params = {"expand": "team.roster"}
        if season:
            params["season"] = season
        cache_suffix = f"{team_id}_{season or 'current'}.json"
        cache_path = Path("roster") / cache_suffix
        endpoint = f"teams/{team_id}"
        return self._request(endpoint, params=params, cache_path=cache_path, use_cache=use_cache)


_DEFAULT_CLIENT: Optional[LegacyStatsClient] = None


def get_default_client() -> LegacyStatsClient:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = LegacyStatsClient()
    return _DEFAULT_CLIENT


def fetch_schedule(start_date: Optional[str] = None, end_date: Optional[str] = None, team_id: Optional[int] = None) -> Dict[str, Any]:
    return get_default_client().get_schedule(start_date=start_date, end_date=end_date, team_id=team_id)


def fetch_game_feed(game_pk: int | str) -> Dict[str, Any]:
    return get_default_client().get_game_feed(game_pk)


def fetch_teams(season: Optional[str] = None) -> Dict[str, Any]:
    return get_default_client().get_teams(season=season)
