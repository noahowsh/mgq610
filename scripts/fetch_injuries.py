#!/usr/bin/env python3
"""Fetch announced injuries/status per team from NHL Stats API."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nhl_prediction.nhl_api import fetch_schedule  # noqa: E402

OUTPUT_PATH = REPO_ROOT / "web" / "src" / "data" / "playerInjuries.json"
GAME_FEED_URL = "https://statsapi.web.nhl.com/api/v1/game/{game_pk}/feed/live"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write roster injury/status summaries.")
    parser.add_argument("--date", required=True, help="Target slate date (YYYY-MM-DD).")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout.")
    return parser.parse_args()


def fetch_live_feed(game_pk: int, timeout: float) -> dict[str, Any] | None:
    try:
        response = requests.get(GAME_FEED_URL.format(game_pk=game_pk), timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def _extract_injuries(feed: dict[str, Any], side: str) -> List[dict[str, Any]]:
    if not feed:
        return []
    players = feed.get("gameData", {}).get("players", {})
    team_players = feed.get("gameData", {}).get("teams", {}).get(side, {})
    team_abbr = (team_players.get("abbreviation") or "").upper()
    result: List[dict[str, Any]] = []
    for player_key, player in players.items():
        status = (player.get("status") or {}).get("code")
        if not status or status.strip().lower() in {"healthy", ""}:
            continue
        if player.get("position", {}).get("code") == "G":
            continue
        result.append(
            {
                "team": team_abbr,
                "playerId": player.get("id"),
                "name": player.get("fullName"),
                "statusCode": player.get("status", {}).get("code"),
                "statusDescription": player.get("status", {}).get("description"),
                "position": player.get("primaryPosition", {}).get("code"),
            }
        )
    return result


def build_payload(date: str, timeout: float) -> dict[str, Any]:
    games = fetch_schedule(date)
    entries: Dict[str, Dict[str, List[dict[str, Any]]]] = {}
    payload_games: List[dict[str, Any]] = []
    for game in games:
        game_id = int(game["gameId"])
        feed = fetch_live_feed(game_id, timeout)
        home_injuries = _extract_injuries(feed, "home")
        away_injuries = _extract_injuries(feed, "away")
        if home_injuries:
            entries.setdefault(home_injuries[0]["team"], {"injuries": []})["injuries"].extend(home_injuries)
        if away_injuries:
            entries.setdefault(away_injuries[0]["team"], {"injuries": []})["injuries"].extend(away_injuries)
        payload_games.append(
            {
                "gameId": str(game_id),
                "date": game.get("gameDate"),
                "home": game.get("homeTeamAbbrev"),
                "away": game.get("awayTeamAbbrev"),
                "homeInjuries": home_injuries,
                "awayInjuries": away_injuries,
            }
        )
    return {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "date": date,
        "teams": entries,
        "games": payload_games,
    }


def main() -> None:
    args = parse_args()
    payload = build_payload(args.date, args.timeout)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"✅ Wrote player injury map → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
