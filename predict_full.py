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
import warnings
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from nhl_prediction.nhl_api import fetch_future_games, fetch_todays_games
from nhl_prediction.pipeline import build_dataset
from nhl_prediction.model import create_baseline_model, fit_model

# Suppress sklearn warnings
warnings.filterwarnings('ignore', category=UserWarning)


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
        
        # Store prediction
        predictions.append({
            'game_num': i,
            'date': game.get('gameDate', date_str),
            'away_team': away_abbrev,
            'home_team': home_abbrev,
            'home_win_prob': prob_home,
            'away_win_prob': prob_away,
            'predicted_winner': home_abbrev if prob_home > 0.5 else away_abbrev,
            'confidence': abs(prob_home - 0.5) * 2  # 0-1 scale
        })
        
        # Display prediction
        print(f"\n{i}. {away_abbrev} @ {home_abbrev}")
        print(f"   Home Win: {prob_home:.1%}  |  Away Win: {prob_away:.1%}")
        
        # Classify prediction strength
        if prob_home > 0.70:
            print(f"   ✅ Prediction: {home_abbrev} STRONG FAVORITE")
        elif prob_home < 0.30:
            print(f"   ✅ Prediction: {away_abbrev} STRONG FAVORITE")
        elif 0.45 <= prob_home <= 0.55:
            print(f"   ⚖️  Prediction: TOSS-UP (too close to call)")
        else:
            favorite = home_abbrev if prob_home > 0.5 else away_abbrev
            confidence = abs(prob_home - 0.5) * 200
            print(f"   📊 Prediction: {favorite} ({confidence:.0f}% confidence)")
    
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
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

