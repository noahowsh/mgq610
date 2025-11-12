#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════╗
║                    PUCKCAST.AI                            ║
║          Data-Driven NHL Prediction Intelligence          ║
╚═══════════════════════════════════════════════════════════╝

FULL MODEL NHL PREDICTIONS
Predict today's games using 141 advanced features

Usage:
    python predict_full.py
    
    # Or predict specific date:
    python predict_full.py 2024-11-15

Requirements:
    - Internet connection (NHL API)
    - Updated MoneyPuck data
"""

import sys
import json
import warnings
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from nhl_prediction.nhl_api import fetch_future_games, fetch_todays_games
from nhl_prediction.pipeline import build_dataset
from nhl_prediction.model import create_baseline_model, fit_model

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning)

WEB_PREDICTIONS_PATH = Path(__file__).parent / "web" / "src" / "data" / "todaysPredictions.json"
ET_ZONE = ZoneInfo("America/New_York")


def format_start_times(start_time_utc: str):
    """Return ISO + human-readable ET string for a UTC start time."""
    if not start_time_utc:
        return None, None

    try:
        dt_utc = datetime.fromisoformat(start_time_utc.replace("Z", "+00:00"))
    except ValueError:
        return None, None

    dt_et = dt_utc.astimezone(ET_ZONE)
    display = dt_et.strftime("%I:%M %p").lstrip("0")
    return dt_utc.isoformat(), f"{display} ET"


def grade_from_edge(edge_value: float) -> str:
    """Map edge (probability delta) to letter grades used on the site."""
    edge_pts = abs(edge_value) * 100
    if edge_pts >= 20:
        return "A+"
    if edge_pts >= 17:
        return "A"
    if edge_pts >= 14:
        return "A-"
    if edge_pts >= 10:
        return "B+"
    if edge_pts >= 7:
        return "B"
    if edge_pts >= 4:
        return "B-"
    if edge_pts >= 2:
        return "C+"
    return "C"


def build_summary(home_team: str, away_team: str, prob_home: float, confidence_grade: str) -> str:
    favorite = home_team if prob_home >= 0.5 else away_team
    favorite_prob = prob_home if favorite == home_team else 1 - prob_home
    edge_pct = abs(prob_home - 0.5) * 100
    direction = "home" if favorite == home_team else "road"
    article = "an" if confidence_grade.startswith("A") else "a"
    return (
        f"{favorite} project at {favorite_prob:.0%} as the {direction} lean — "
        f"{article} {confidence_grade}-tier edge worth {edge_pct:.1f} pts over a coin flip."
    )


def export_predictions_json(predictions, generated_at=None):
    """Write predictions for the web landing page in JSON format."""
    WEB_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generatedAt": (generated_at or datetime.now(timezone.utc).isoformat()),
        "games": [],
    }

    for pred in predictions:
        payload["games"].append(
            {
                "id": str(pred.get("game_id", pred.get("game_num"))),
                "gameDate": pred.get("date"),
                "startTimeEt": pred.get("start_time_et"),
                "startTimeUtc": pred.get("start_time_utc"),
                "homeTeam": {
                    "name": pred.get("home_team_name", pred.get("home_team")),
                    "abbrev": pred.get("home_team"),
                },
                "awayTeam": {
                    "name": pred.get("away_team_name", pred.get("away_team")),
                    "abbrev": pred.get("away_team"),
                },
                "homeWinProb": round(pred.get("home_win_prob", 0.0), 4),
                "awayWinProb": round(pred.get("away_win_prob", 0.0), 4),
                "confidenceScore": round(pred.get("confidence", 0.0), 3),
                "confidenceGrade": pred.get("confidence_grade", "C"),
                "edge": round(pred.get("edge", 0.0), 3),
                "summary": pred.get("summary", ""),
                "modelFavorite": pred.get("model_favorite", "home"),
                "venue": pred.get("venue"),
                "season": str(pred.get("season")) if pred.get("season") else None,
            }
        )

    WEB_PREDICTIONS_PATH.write_text(json.dumps(payload, indent=2))
    print(f"\n🛰  Exported web payload → {WEB_PREDICTIONS_PATH}")


def predict_games(date=None, num_games=20):
    """
    Predict NHL games using full model with all features.
    
    Args:
        date: Date string 'YYYY-MM-DD' or None for today
        num_games: Number of games to predict (default 20)
    """
    
    print("━"*80)
    print("🏒 PUCKCAST.AI - NHL PREDICTIONS")
    print("   Data-Driven Intelligence for Today's Games")
    print("━"*80)
    
    # Get date
    if date is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
        date_display = datetime.now().strftime('%A, %B %d, %Y')
    else:
        date_str = date
        date_display = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
    
    print(f"\n📅 Date: {date_display}")
    
    # Step 1: Fetch games
    print(f"\n1️⃣  Fetching games for {date_str}...")
    
    if date is None:
        games = fetch_todays_games()
    else:
        games = fetch_future_games(date_str)
    
    if not games:
        print(f"   ℹ️  No games scheduled for {date_str}")
        return []
    
    print(f"   ✅ Found {len(games)} games")
    
    # Step 2: Build dataset
    print("\n2️⃣  Building dataset with ALL features...")
    print("   (Loading 4 full seasons: 2021-2025, ~5,600+ games...)")
    print("   ⚠️  Skipping 2020 COVID-shortened season")
    
    # Load 2021-2025 (skip 2020 COVID season)
    dataset = build_dataset(['20212022', '20222023', '20232024', '20242025'])
    
    print(f"   ✅ {len(dataset.games)} games loaded")
    print(f"   ✅ {dataset.features.shape[1]} features engineered")
    
    # Step 3: Train model
    print("\n3️⃣  Training model on 2021-2024 seasons (4 full seasons)...")
    
    # Train on 2021-2024, test on 2025 (current season)
    train_mask = dataset.games['seasonId'].isin(['20212022', '20222023', '20232024', '20242025'])
    # Only train on games before prediction date
    predict_date = datetime.strptime(date_str, '%Y-%m-%d') if date else datetime.now()
    train_mask = train_mask & (dataset.games['gameDate'] < predict_date)
    
    model = create_baseline_model(C=1.0)
    model = fit_model(model, dataset.features, dataset.target, train_mask)
    
    print(f"   ✅ Trained on {train_mask.sum():,} historical games (2021-2024)")
    
    # Step 4: Predict
    print(f"\n4️⃣  Generating predictions for {min(num_games, len(games))} games...")
    
    print("\n" + "="*80)
    print("PREDICTIONS")
    print("="*80)
    
    predictions = []
    
    for i, game in enumerate(games[:num_games], 1):
        home_id = game['homeTeamId']
        away_id = game['awayTeamId']
        home_abbrev = game['homeTeamAbbrev']
        away_abbrev = game['awayTeamAbbrev']
        
        # Find most recent games for each team
        home_recent = dataset.games[
            (dataset.games['teamId_home'] == home_id) & 
            (dataset.games['seasonId'] == '20242025')
        ].tail(1)
        
        away_recent = dataset.games[
            (dataset.games['teamId_away'] == away_id) & 
            (dataset.games['seasonId'] == '20242025')
        ].tail(1)
        
        if len(home_recent) == 0 or len(away_recent) == 0:
            print(f"\n{i}. {away_abbrev} @ {home_abbrev}")
            print(f"   ⚠️  Insufficient data (team hasn't played this season)")
            continue
        
        # Get feature vectors
        home_idx = home_recent.index[0]
        away_idx = away_recent.index[0]
        
        home_features = dataset.features.loc[home_idx]
        away_features = dataset.features.loc[away_idx]
        
        # Create matchup features (average of recent performance)
        matchup_features = (home_features + away_features) / 2
        
        # Predict with full model
        prob_home = model.predict_proba(matchup_features.values.reshape(1, -1))[0][1]
        prob_away = 1 - prob_home

        start_time_utc_iso, start_time_et = format_start_times(game.get('startTimeUTC', ''))
        edge = prob_home - 0.5
        confidence_score = abs(edge) * 2  # 0-1 scale
        confidence_grade = grade_from_edge(edge)
        model_favorite = 'home' if prob_home >= prob_away else 'away'
        summary = build_summary(game.get('homeTeamName', home_abbrev), game.get('awayTeamName', away_abbrev), prob_home, confidence_grade)
        
        # Store prediction
        predictions.append({
            'game_num': i,
            'game_id': game.get('gameId'),
            'date': game.get('gameDate', date_str),
            'season': game.get('season'),
            'venue': game.get('venue'),
            'game_state': game.get('gameState'),
            'start_time_utc': start_time_utc_iso,
            'start_time_et': start_time_et,
            'away_team': away_abbrev,
            'away_team_name': game.get('awayTeamName', away_abbrev),
            'home_team': home_abbrev,
            'home_team_name': game.get('homeTeamName', home_abbrev),
            'home_win_prob': prob_home,
            'away_win_prob': prob_away,
            'edge': edge,
            'predicted_winner': home_abbrev if prob_home > 0.5 else away_abbrev,
            'model_favorite': model_favorite,
            'confidence': confidence_score,
            'confidence_grade': confidence_grade,
            'summary': summary
        })
        
        # Display prediction
        print(f"\n{i}. {away_abbrev} @ {home_abbrev}")
        print(f"   Home Win: {prob_home:.1%}  |  Away Win: {prob_away:.1%}")
        
        # Classify prediction strength
        confidence_pct = confidence_score * 100

        if prob_home > 0.70:
            print(f"   ✅ Prediction: {home_abbrev} STRONG FAVORITE")
        elif prob_home < 0.30:
            print(f"   ✅ Prediction: {away_abbrev} STRONG FAVORITE")
        elif 0.45 <= prob_home <= 0.55:
            print(f"   ⚖️  Prediction: TOSS-UP (too close to call)")
        else:
            favorite = home_abbrev if prob_home > 0.5 else away_abbrev
            print(f"   📊 Prediction: {favorite} ({confidence_pct:.0f}% confidence)")
    
    # Summary
    print("\n" + "="*80)
    print(f"✅ PREDICTIONS COMPLETE")
    print(f"   Total Games: {len(predictions)}")
    print(f"   Model: Logistic Regression with {dataset.features.shape[1]} features")
    print(f"   Training: {train_mask.sum()} games from 2022-2024 seasons")
    print("="*80)
    
    return predictions


def main():
    """Main entry point."""
    
    # Parse command line args - simple: just date (optional)
    # Usage: python predict_full.py [YYYY-MM-DD]
    if len(sys.argv) > 1:
        date_arg = sys.argv[1]
        # Skip if it's a flag like --date
        if date_arg.startswith('--'):
            date = None
            print("\nPredicting today's games...")
        else:
            date = date_arg
            print(f"\nPredicting games for: {date}")
    else:
        date = None
        print("\nPredicting today's games...")
    
    try:
        predictions = predict_games(date=date, num_games=20)

        # Save to CSV
        if predictions:
            df = pd.DataFrame(predictions)
            filename = f"predictions_{date or datetime.now().strftime('%Y-%m-%d')}.csv"
            df.to_csv(filename, index=False)
            print(f"\n💾 Saved predictions to: {filename}")

        export_predictions_json(predictions, generated_at=datetime.now(timezone.utc).isoformat())
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
