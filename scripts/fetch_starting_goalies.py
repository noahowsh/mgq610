#!/usr/bin/env python3
"""Fetch day-of starting goalies + injury status from the NHL Stats API."""

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

OUTPUT_PATH = REPO_ROOT / "web" / "src" / "data" / "startingGoalies.json"
GAME_FEED_URL = "https://statsapi.web.nhl.com/api/v1/game/{game_pk}/feed/live"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grab NHL starting goalie confirmations.")
    parser.add_argument("--date", required=True, help="Date string (YYYY-MM-DD).")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout (seconds).")
    return parser.parse_args()


def fetch_live_feed(game_pk: int, timeout: float) -> dict[str, Any] | None:
    try:
        response = requests.get(GAME_FEED_URL.format(game_pk=game_pk), timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def _extract_goalie(feed: dict[str, Any], side: str) -> dict[str, Any] | None:
    if not feed:
        return None
    players = feed.get("gameData", {}).get("players", {})
    teams = feed.get("gameData", {}).get("teams", {})
    target = teams.get(side, {})
    abbrev = (target.get("abbreviation") or "").upper()
    goalie_ids = feed.get("liveData", {}).get("boxscore", {}).get("teams", {}).get(side, {}).get("goalies", [])
    if not goalie_ids:
        return {"team": abbrev, "confirmedStart": False}
    goalie_id = goalie_ids[0]
    player_key = f"ID{goalie_id}"
    player = players.get(player_key, {})
    status = player.get("status", {}) or {}
    return {
        "team": abbrev,
        "playerId": goalie_id,
        "goalieName": player.get("fullName"),
        "confirmedStart": True,
        "statusCode": status.get("code"),
        "statusDescription": status.get("description"),
    }


def build_payload(date: str, timeout: float) -> dict[str, Any]:
    games = fetch_schedule(date)
    payload = {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "date": date,
        "teams": {},
        "games": [],
    }
    for game in games:
        game_id = int(game["gameId"])
        feed = fetch_live_feed(game_id, timeout)
        home = _extract_goalie(feed, "home")
        away = _extract_goalie(feed, "away")
        if home and home.get("team"):
            payload["teams"][home["team"]] = home
        if away and away.get("team"):
            payload["teams"][away["team"]] = away
        payload["games"].append(
            {
                "gameId": str(game_id),
                "homeTeam": game.get("homeTeamAbbrev"),
                "awayTeam": game.get("awayTeamAbbrev"),
                "homeGoalie": home,
                "awayGoalie": away,
            }
        )
    return payload


def main() -> None:
    args = parse_args()
    payload = build_payload(args.date, args.timeout)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"✅ Wrote starting goalie data → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
