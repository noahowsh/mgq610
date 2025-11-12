"""Client for NHL Stats REST reports."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests

from .cache import JSONCache

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://api.nhle.com/stats/rest"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_ROOT = PROJECT_ROOT / "data" / "raw" / "stats_rest"


def build_cayenne(filters: Dict[str, Any]) -> str:
    """Convert a dict into a Stats REST cayenne expression."""
    parts = []
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, str):
            parts.append(f"{key}='{value}'")
        else:
            parts.append(f"{key}={value}")
    return " and ".join(parts)


class StatsRestClient:
    """Rate-limited helper for hitting stats/rest endpoints."""

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
        path: str,
        *,
        lang: str = "en",
        params: Optional[Dict[str, Any]] = None,
        cache_path: Optional[Path | str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        url = f"{BASE_URL}/{lang.strip('/')}/{path.lstrip('/')}"

        if use_cache and cache_path is not None:
            cached = self.cache.read(cache_path)
            if cached is not None:
                return cached

        self._rate_limit()
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if cache_path is not None:
            self.cache.write(cache_path, payload)

        return payload

    @staticmethod
    def to_dataframe(payload: Dict[str, Any]) -> pd.DataFrame:
        data = payload.get("data", [])
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)

    def get_config(self, *, lang: str = "en", use_cache: bool = True) -> Dict[str, Any]:
        cache_path = Path("config") / f"{lang}.json"
        return self._request("config", lang=lang, cache_path=cache_path, use_cache=use_cache)

    def fetch_report(
        self,
        report_path: str,
        *,
        lang: str = "en",
        params: Optional[Dict[str, Any]] = None,
        cache_path: Optional[Path | str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        return self._request(report_path, lang=lang, params=params, cache_path=cache_path, use_cache=use_cache)

    def get_team_summary(
        self,
        season_id: str,
        *,
        lang: str = "en",
        game_type_id: int = 2,
        is_aggregate: bool = True,
        limit: int = -1,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        filters = {"seasonId": season_id, "gameTypeId": game_type_id}
        params = {
            "isAggregate": str(is_aggregate).lower(),
            "cayenneExp": build_cayenne(filters),
            "limit": limit,
        }
        cache_path = Path("team") / "summary" / f"{season_id}_gt{game_type_id}.json"
        payload = self.fetch_report("team/summary", lang=lang, params=params, cache_path=cache_path, use_cache=use_cache)
        return self.to_dataframe(payload)

    def get_goalie_summary(
        self,
        season_id: str,
        *,
        lang: str = "en",
        game_type_id: int = 2,
        limit: int = -1,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        filters = {"seasonId": season_id, "gameTypeId": game_type_id}
        params = {
            "isAggregate": "true",
            "cayenneExp": build_cayenne(filters),
            "limit": limit,
        }
        cache_path = Path("goalie") / "summary" / f"{season_id}_gt{game_type_id}.json"
        payload = self.fetch_report("goalie/summary", lang=lang, params=params, cache_path=cache_path, use_cache=use_cache)
        return self.to_dataframe(payload)

    def get_skater_report(
        self,
        report: str,
        *,
        filters: Optional[Dict[str, Any]] = None,
        lang: str = "en",
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        params = dict(params or {})
        if filters:
            params["cayenneExp"] = build_cayenne(filters)
        cache_suffix = params.get("cayenneExp", "all").replace(" ", "_")
        cache_path = Path("skater") / report / f"{cache_suffix}.json"
        payload = self.fetch_report(f"skater/{report}", lang=lang, params=params, cache_path=cache_path, use_cache=use_cache)
        return self.to_dataframe(payload)

    def get_shift_chart(
        self,
        game_id: int | str,
        *,
        lang: str = "en",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        params = {"cayenneExp": f"gameId={game_id}"}
        cache_path = Path("shiftcharts") / f"{game_id}.json"
        payload = self.fetch_report("shiftcharts", lang=lang, params=params, cache_path=cache_path, use_cache=use_cache)
        return self.to_dataframe(payload)


_DEFAULT_CLIENT: Optional[StatsRestClient] = None


def get_default_client() -> StatsRestClient:
    global _DEFAULT_CLIENT
    if _DEFAULT_CLIENT is None:
        _DEFAULT_CLIENT = StatsRestClient()
    return _DEFAULT_CLIENT


def fetch_team_summary(season_id: str, game_type_id: int = 2) -> pd.DataFrame:
    return get_default_client().get_team_summary(season_id, game_type_id=game_type_id)


def fetch_goalie_summary(season_id: str, game_type_id: int = 2) -> pd.DataFrame:
    return get_default_client().get_goalie_summary(season_id, game_type_id=game_type_id)


def fetch_shift_chart(game_id: int | str) -> pd.DataFrame:
    return get_default_client().get_shift_chart(game_id)


def fetch_config() -> Dict[str, Any]:
    return get_default_client().get_config()
