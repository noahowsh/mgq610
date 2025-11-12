"""Client for the NHL Web API (v1) Gamecenter endpoints."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .cache import JSONCache

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://api-web.nhle.com/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_ROOT = PROJECT_ROOT / "data" / "raw" / "web_v1"


def _season_bucket(game_id: int | str) -> str:
    text = str(game_id)
    return text[:4] if len(text) >= 4 else "unknown"


class GamecenterClient:
    """Lightweight wrapper around commonly used Web v1 routes."""

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

    def get_play_by_play(self, game_id: int | str, *, use_cache: bool = True) -> Dict[str, Any]:
        cache_path = Path(_season_bucket(game_id)) / f"{game_id}_pbp.json"
        endpoint = f"gamecenter/{game_id}/play-by-play"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_boxscore(self, game_id: int | str, *, use_cache: bool = True) -> Dict[str, Any]:
        cache_path = Path(_season_bucket(game_id)) / f"{game_id}_boxscore.json"
        endpoint = f"gamecenter/{game_id}/boxscore"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_team_schedule(self, team_abbrev: str, season: str, *, use_cache: bool = True) -> Dict[str, Any]:
        team = team_abbrev.lower()
        cache_path = Path("schedules") / season / f"{team}.json"
        endpoint = f"club-schedule-season/{team}/{season}"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_schedule(self, date_str: str, *, use_cache: bool = True) -> Dict[str, Any]:
        cache_path = Path("schedule") / f"{date_str}.json"
        endpoint = f"schedule/{date_str}"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_roster(self, team_abbrev: str, season: str = "current", *, use_cache: bool = True) -> Dict[str, Any]:
        team = team_abbrev.upper()
        cache_path = Path("rosters") / season / f"{team}.json"
        endpoint = f"roster/{team}/{season}"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_standings(self, season: str, *, use_cache: bool = True) -> Dict[str, Any]:
        cache_path = Path("standings") / f"{season}.json"
        endpoint = f"standings/{season}"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)

    def get_edge(self, path: str, *, use_cache: bool = True) -> Dict[str, Any]:
        """Access miscellaneous /edge routes for supplemental data."""
        cache_path = Path("edge") / f"{path.replace('/', '_')}.json"
        endpoint = f"cat/{path.lstrip('/')}"
        return self._request(endpoint, cache_path=cache_path, use_cache=use_cache)


_DEFAULT_CLIENT: Optional[GamecenterClient] = None


def get_default_client() -> GamecenterClient:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = GamecenterClient()
    return _DEFAULT_CLIENT


def fetch_play_by_play(game_id: int | str) -> Dict[str, Any]:
    return get_default_client().get_play_by_play(game_id)


def fetch_boxscore(game_id: int | str) -> Dict[str, Any]:
    return get_default_client().get_boxscore(game_id)


def fetch_team_schedule(team_abbrev: str, season: str) -> Dict[str, Any]:
    return get_default_client().get_team_schedule(team_abbrev, season)


def fetch_schedule(date_str: str) -> Dict[str, Any]:
    return get_default_client().get_schedule(date_str)


def fetch_roster(team_abbrev: str, season: str = "current") -> Dict[str, Any]:
    return get_default_client().get_roster(team_abbrev, season)


def fetch_standings(season: str) -> Dict[str, Any]:
    return get_default_client().get_standings(season)
