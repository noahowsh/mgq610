"""Betting analysis and simulation utilities for NHL prediction model."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd


def american_to_probability(odds: float) -> float:
    """
    Convert American odds to implied probability.
    
    Args:
        odds: American odds (negative for favorites, positive for underdogs)
              e.g., -150, +130
    
    Returns:
        Implied probability (0 to 1)
    
    Examples:
        >>> american_to_probability(-150)
        0.6
        >>> american_to_probability(130)
        0.43478...
    """
    if odds < 0:
        # Favorite: odds of -150 means bet $150 to win $100
        return abs(odds) / (abs(odds) + 100)
    else:
        # Underdog: odds of +130 means bet $100 to win $130
        return 100 / (odds + 100)


def remove_vig_proportional(prob_home: float, prob_away: float) -> Tuple[float, float]:
    """
    Remove bookmaker's vig (overround) using proportional method.
    
    Bookmakers set odds so that implied probabilities sum to > 100%.
    This function scales probabilities proportionally to sum to exactly 100%.
    
    Args:
        prob_home: Raw implied probability for home team (with vig)
        prob_away: Raw implied probability for away team (with vig)
    
    Returns:
        Tuple of (true_prob_home, true_prob_away) summing to 1.0
    
    Example:
        >>> remove_vig_proportional(0.60, 0.4348)
        (0.5799, 0.4201)
    """
    total = prob_home + prob_away
    true_prob_home = prob_home / total
    true_prob_away = prob_away / total
    return true_prob_home, true_prob_away


def process_betting_odds(odds_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process betting odds DataFrame to extract true market probabilities.
    
    Args:
        odds_df: DataFrame with columns ['game_id', 'home_odds', 'away_odds']
                 Odds should be in American format
    
    Returns:
        DataFrame with additional columns:
            - home_prob_raw: implied probability from home odds
            - away_prob_raw: implied probability from away odds
            - total_prob: sum of raw probabilities (should be > 1.0)
            - vig_percent: bookmaker's edge percentage
            - market_prob_home: true market probability (vig removed)
            - market_prob_away: true market probability (vig removed)
    """
    result = odds_df.copy()
    
    # Convert odds to raw probabilities
    result['home_prob_raw'] = result['home_odds'].apply(american_to_probability)
    result['away_prob_raw'] = result['away_odds'].apply(american_to_probability)
    
    # Calculate vig
    result['total_prob'] = result['home_prob_raw'] + result['away_prob_raw']
    result['vig_percent'] = (result['total_prob'] - 1.0) * 100
    
    # Remove vig using proportional method
    vig_removed = result.apply(
        lambda row: remove_vig_proportional(row['home_prob_raw'], row['away_prob_raw']),
        axis=1
    )
    result['market_prob_home'] = [x[0] for x in vig_removed]
    result['market_prob_away'] = [x[1] for x in vig_removed]
    
    return result


def calculate_payout(bet_amount: float, odds: float, won: bool) -> float:
    """
    Calculate payout (profit) from a bet.
    
    Args:
        bet_amount: Amount wagered
        odds: American odds
        won: Whether the bet won
    
    Returns:
        Profit (positive) or loss (negative)
    """
    if not won:
        return -bet_amount
    
    # Calculate winnings based on American odds
    if odds < 0:
        # Favorite: bet $150 to win $100 → profit = bet × (100 / |odds|)
        profit = bet_amount * (100 / abs(odds))
    else:
        # Underdog: bet $100 to win $130 → profit = bet × (odds / 100)
        profit = bet_amount * (odds / 100)
    
    return profit


def kelly_criterion(model_prob: float, odds: float) -> float:
    """
    Calculate optimal bet size using Kelly Criterion.
    
    Kelly formula: f* = (p × b - q) / b
    where:
        p = probability of winning (model estimate)
        q = 1 - p (probability of losing)
        b = net decimal odds (payout per dollar wagered)
    
    Args:
        model_prob: Model's estimated probability of winning
        odds: American odds
    
    Returns:
        Fraction of bankroll to bet (0 to 1)
        Returns 0 if Kelly is negative (no bet)
    """
    # Convert American odds to decimal odds
    if odds < 0:
        decimal_odds = 1 + (100 / abs(odds))
    else:
        decimal_odds = 1 + (odds / 100)
    
    b = decimal_odds - 1  # net odds (profit per dollar)
    p = model_prob
    q = 1 - p
    
    # Kelly fraction
    kelly_frac = (p * b - q) / b
    
    # Never bet if Kelly is negative (negative expected value)
    return max(0.0, kelly_frac)


def simulate_threshold_betting(
    games_df: pd.DataFrame,
    edge_threshold: float = 0.05,
    bet_size: float = 100.0,
) -> Tuple[pd.DataFrame, float]:
    """
    Simulate fixed-stake betting strategy based on probability edge threshold.
    
    Strategy: Bet fixed amount when model probability exceeds market probability
              by at least edge_threshold.
    
    Args:
        games_df: DataFrame with columns:
            - model_prob_home: model's predicted probability of home win
            - market_prob_home: market's probability (vig removed)
            - home_odds: American odds for home team
            - away_odds: American odds for away team
            - home_win: actual outcome (1 if home won, 0 if away won)
            - game_id (optional): game identifier
        edge_threshold: minimum probability edge to place bet (e.g., 0.05 = 5%)
        bet_size: fixed stake per bet in dollars
    
    Returns:
        Tuple of (bets_df, final_bankroll) where:
            - bets_df: DataFrame with one row per bet placed
            - final_bankroll: cumulative profit/loss
    """
    results = []
    bankroll = 0.0
    
    for idx, game in games_df.iterrows():
        # Calculate edge for both home and away
        edge_home = game['model_prob_home'] - game['market_prob_home']
        edge_away = (1 - game['model_prob_home']) - (1 - game['market_prob_home'])
        
        bet_placed = None
        profit = 0.0
        
        # Check if we have sufficient edge on home team
        if edge_home >= edge_threshold:
            bet_placed = 'home'
            won = game['home_win'] == 1
            profit = calculate_payout(bet_size, game['home_odds'], won)
        
        # Check if we have sufficient edge on away team
        elif edge_away >= edge_threshold:
            bet_placed = 'away'
            won = game['home_win'] == 0
            profit = calculate_payout(bet_size, game['away_odds'], won)
        
        if bet_placed:
            bankroll += profit
            results.append({
                'game_id': game.get('game_id', idx),
                'bet_on': bet_placed,
                'edge': edge_home if bet_placed == 'home' else edge_away,
                'model_prob': game['model_prob_home'] if bet_placed == 'home' else (1 - game['model_prob_home']),
                'market_prob': game['market_prob_home'] if bet_placed == 'home' else (1 - game['market_prob_home']),
                'odds': game['home_odds'] if bet_placed == 'home' else game['away_odds'],
                'bet_size': bet_size,
                'outcome': 'win' if profit > 0 else 'loss',
                'profit': profit,
                'cumulative_profit': bankroll,
            })
    
    return pd.DataFrame(results), bankroll


def simulate_kelly_betting(
    games_df: pd.DataFrame,
    kelly_fraction: float = 0.25,
    starting_bankroll: float = 10000.0,
) -> Tuple[pd.DataFrame, float]:
    """
    Simulate Kelly Criterion betting strategy with fractional Kelly.
    
    Strategy: Bet a fraction of current bankroll proportional to edge,
              using Kelly Criterion to optimize bet sizing.
    
    Args:
        games_df: DataFrame with columns:
            - model_prob_home, market_prob_home, home_odds, away_odds, home_win
            - game_id (optional)
        kelly_fraction: fraction of full Kelly to bet (e.g., 0.25 = "quarter Kelly")
                       Lower fractions reduce variance but also reduce growth rate
        starting_bankroll: initial bankroll in dollars
    
    Returns:
        Tuple of (bets_df, final_bankroll)
    """
    bankroll = starting_bankroll
    results = []
    
    for idx, game in games_df.iterrows():
        # Calculate edge for both sides
        edge_home = game['model_prob_home'] - game['market_prob_home']
        edge_away = (1 - game['model_prob_home']) - (1 - game['market_prob_home'])
        
        bet_placed = None
        bet_size = 0.0
        odds = 0.0
        won = False
        
        # Determine which side (if any) has positive edge
        if edge_home > 0:
            kelly = kelly_criterion(game['model_prob_home'], game['home_odds'])
            bet_size = bankroll * kelly * kelly_fraction
            if bet_size >= 1.0:  # Minimum $1 bet
                bet_placed = 'home'
                odds = game['home_odds']
                won = game['home_win'] == 1
        
        elif edge_away > 0:
            kelly = kelly_criterion(1 - game['model_prob_home'], game['away_odds'])
            bet_size = bankroll * kelly * kelly_fraction
            if bet_size >= 1.0:
                bet_placed = 'away'
                odds = game['away_odds']
                won = game['home_win'] == 0
        
        if bet_placed and bet_size > 0:
            profit = calculate_payout(bet_size, odds, won)
            bankroll += profit
            
            results.append({
                'game_id': game.get('game_id', idx),
                'bet_on': bet_placed,
                'edge': edge_home if bet_placed == 'home' else edge_away,
                'model_prob': game['model_prob_home'] if bet_placed == 'home' else (1 - game['model_prob_home']),
                'market_prob': game['market_prob_home'] if bet_placed == 'home' else (1 - game['market_prob_home']),
                'odds': odds,
                'bet_size': bet_size,
                'outcome': 'win' if profit > 0 else 'loss',
                'profit': profit,
                'bankroll': bankroll,
                'roi': ((bankroll - starting_bankroll) / starting_bankroll) * 100,
            })
    
    return pd.DataFrame(results), bankroll


def calculate_roi_metrics(bets_df: pd.DataFrame, bet_size: float = None) -> Dict[str, float]:
    """
    Calculate comprehensive ROI metrics from betting results.
    
    Args:
        bets_df: DataFrame of betting results (from simulate_*_betting)
        bet_size: fixed bet size (for fixed-stake strategies)
                  If None, uses actual bet_size column
    
    Returns:
        Dictionary with metrics:
            - n_bets: number of bets placed
            - total_wagered: total amount bet
            - total_profit: net profit/loss
            - roi_percent: return on investment percentage
            - win_rate: proportion of bets won
            - avg_profit_per_bet: average profit per bet
            - sharpe_ratio: risk-adjusted return
            - max_drawdown: largest cumulative loss from peak
    """
    if len(bets_df) == 0:
        return {
            'n_bets': 0,
            'total_wagered': 0.0,
            'total_profit': 0.0,
            'roi_percent': 0.0,
            'win_rate': 0.0,
            'avg_profit_per_bet': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
        }
    
    n_bets = len(bets_df)
    
    # Total wagered
    if bet_size is not None:
        total_wagered = n_bets * bet_size
    else:
        total_wagered = bets_df['bet_size'].sum()
    
    # Profit metrics
    total_profit = bets_df['profit'].sum()
    roi_percent = (total_profit / total_wagered * 100) if total_wagered > 0 else 0.0
    avg_profit = bets_df['profit'].mean()
    
    # Win rate
    win_rate = (bets_df['outcome'] == 'win').mean()
    
    # Sharpe ratio (annualized, assuming ~1300 games per season)
    returns = bets_df['profit']
    if returns.std() > 0:
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(len(returns))
    else:
        sharpe_ratio = 0.0
    
    # Maximum drawdown
    cumulative = bets_df['cumulative_profit'].values if 'cumulative_profit' in bets_df else bets_df['profit'].cumsum().values
    running_max = np.maximum.accumulate(cumulative)
    drawdown = running_max - cumulative
    max_drawdown = drawdown.max()
    
    return {
        'n_bets': n_bets,
        'total_wagered': total_wagered,
        'total_profit': total_profit,
        'roi_percent': roi_percent,
        'win_rate': win_rate,
        'avg_profit_per_bet': avg_profit,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
    }


def compare_model_vs_market(predictions_df: pd.DataFrame) -> Dict[str, float]:
    """
    Compare model probabilities against market probabilities.
    
    Args:
        predictions_df: DataFrame with columns:
            - model_prob_home: model predictions
            - market_prob_home: market probabilities (vig removed)
            - home_win: actual outcomes
    
    Returns:
        Dictionary with comparison metrics:
            - model_brier_score: model's Brier score (lower is better)
            - market_brier_score: market's Brier score
            - model_log_loss: model's log loss
            - market_log_loss: market's log loss
            - mean_prob_diff: average difference (model - market)
            - abs_mean_prob_diff: average absolute difference
            - correlation: correlation between model and market probs
    """
    from sklearn.metrics import brier_score_loss, log_loss
    
    y_true = predictions_df['home_win']
    model_probs = predictions_df['model_prob_home']
    market_probs = predictions_df['market_prob_home']
    
    # Clip probabilities to avoid log(0) errors
    model_probs_clipped = np.clip(model_probs, 1e-6, 1 - 1e-6)
    market_probs_clipped = np.clip(market_probs, 1e-6, 1 - 1e-6)
    
    return {
        'model_brier_score': brier_score_loss(y_true, model_probs),
        'market_brier_score': brier_score_loss(y_true, market_probs),
        'model_log_loss': log_loss(y_true, model_probs_clipped),
        'market_log_loss': log_loss(y_true, market_probs_clipped),
        'mean_prob_diff': (model_probs - market_probs).mean(),
        'abs_mean_prob_diff': np.abs(model_probs - market_probs).mean(),
        'correlation': np.corrcoef(model_probs, market_probs)[0, 1],
    }


__all__ = [
    'american_to_probability',
    'remove_vig_proportional',
    'process_betting_odds',
    'calculate_payout',
    'kelly_criterion',
    'simulate_threshold_betting',
    'simulate_kelly_betting',
    'calculate_roi_metrics',
    'compare_model_vs_market',
]



