"""
Generate comprehensive prediction analysis visualizations.

This script creates:
1. Win rate by confidence level
2. Calibration across probability bins
3. Error analysis (when does model fail?)
4. Prediction distribution
5. Confidence vs accuracy relationship

Usage:
    python -m nhl_prediction.create_prediction_analysis
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def load_predictions():
    """Load prediction data."""
    predictions = pd.read_csv('reports/predictions_20232024.csv')
    predictions['gameDate'] = pd.to_datetime(predictions['gameDate'])
    return predictions

def create_confidence_bins(predictions):
    """Create probability bins for analysis."""
    # Create bins: 50-55%, 55-60%, 60-65%, 65-70%, 70-75%, 75%+
    bins = [0.5, 0.55, 0.60, 0.65, 0.70, 0.75, 1.0]
    labels = ['50-55%', '55-60%', '60-65%', '65-70%', '70-75%', '75%+']
    predictions['confidence_bin'] = pd.cut(
        predictions['home_win_probability'], 
        bins=bins, 
        labels=labels,
        include_lowest=True
    )
    return predictions

def plot_win_rate_by_confidence(predictions, ax):
    """Plot win rate across different confidence levels."""
    # Group by confidence bin
    confidence_analysis = predictions.groupby('confidence_bin', observed=True).agg({
        'home_win': 'mean',
        'correct': 'mean',
        'gameId': 'count'
    }).reset_index()
    confidence_analysis.columns = ['Confidence', 'Home Win Rate', 'Model Accuracy', 'Count']
    
    # Create bar plot
    x = np.arange(len(confidence_analysis))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, confidence_analysis['Home Win Rate'] * 100, 
                   width, label='Actual Home Win Rate', color='#2ecc71', alpha=0.8)
    bars2 = ax.bar(x + width/2, confidence_analysis['Model Accuracy'] * 100, 
                   width, label='Model Accuracy', color='#3498db', alpha=0.8)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=8)
    
    # Add count labels below
    for i, count in enumerate(confidence_analysis['Count']):
        ax.text(i, -8, f'n={count}', ha='center', fontsize=8, color='gray')
    
    ax.set_xlabel('Model Confidence (Home Win Probability)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Percentage', fontsize=11, fontweight='bold')
    ax.set_title('Model Performance by Confidence Level', fontsize=13, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(confidence_analysis['Confidence'], rotation=0)
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, 100)
    
    # Add reference line at 50%
    ax.axhline(y=50, color='red', linestyle='--', alpha=0.3, linewidth=1)

def plot_calibration_bins(predictions, ax):
    """Plot calibration curve with binned probabilities."""
    # Create 10 bins
    n_bins = 10
    bin_edges = np.linspace(0.5, 1.0, n_bins + 1)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    # Calculate observed frequency in each bin
    observed_freq = []
    counts = []
    
    for i in range(n_bins):
        mask = (predictions['home_win_probability'] >= bin_edges[i]) & \
               (predictions['home_win_probability'] < bin_edges[i + 1])
        if i == n_bins - 1:  # Include upper bound in last bin
            mask = (predictions['home_win_probability'] >= bin_edges[i]) & \
                   (predictions['home_win_probability'] <= bin_edges[i + 1])
        
        if mask.sum() > 0:
            observed_freq.append(predictions.loc[mask, 'home_win'].mean())
            counts.append(mask.sum())
        else:
            observed_freq.append(np.nan)
            counts.append(0)
    
    # Plot
    ax.plot([0.5, 1.0], [0.5, 1.0], 'r--', linewidth=2, label='Perfect Calibration', alpha=0.7)
    
    # Plot points sized by count
    scatter = ax.scatter(bin_centers, observed_freq, s=[c*2 for c in counts], 
                        c=counts, cmap='YlOrRd', alpha=0.7, edgecolors='black', linewidth=1.5)
    
    # Connect points
    valid_mask = ~np.isnan(observed_freq)
    ax.plot(bin_centers[valid_mask], np.array(observed_freq)[valid_mask], 
           'b-', linewidth=2, alpha=0.5)
    
    # Add colorbar for counts
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Number of Games', rotation=270, labelpad=15)
    
    ax.set_xlabel('Predicted Probability (Home Win)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Observed Frequency (Actual Home Wins)', fontsize=11, fontweight='bold')
    ax.set_title('Calibration Analysis: Predicted vs Observed', fontsize=13, fontweight='bold', pad=15)
    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(alpha=0.3)
    ax.set_xlim(0.48, 1.02)
    ax.set_ylim(0.48, 1.02)
    ax.set_aspect('equal')

def plot_error_analysis(predictions, ax):
    """Analyze when model makes errors."""
    # Categorize predictions
    def categorize_prediction(row):
        prob = row['home_win_probability']
        correct = row['correct']
        home_win = row['home_win']
        
        if correct:
            if prob >= 0.65:
                return 'Correct (High Conf)'
            else:
                return 'Correct (Low Conf)'
        else:
            if prob >= 0.65:
                return 'Wrong (High Conf)'
            else:
                return 'Wrong (Low Conf)'
    
    predictions['outcome_category'] = predictions.apply(categorize_prediction, axis=1)
    
    # Count by category
    category_counts = predictions['outcome_category'].value_counts()
    
    # Create pie chart with better colors
    colors = ['#2ecc71', '#95a5a6', '#e74c3c', '#e67e22']
    explode = [0, 0, 0.1, 0.05]  # Explode the error slices
    
    wedges, texts, autotexts = ax.pie(
        category_counts.values, 
        labels=category_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        explode=explode,
        shadow=True,
        textprops={'fontsize': 10, 'fontweight': 'bold'}
    )
    
    # Make percentage text white and bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(11)
    
    # Add counts to legend
    legend_labels = [f'{cat}: {count} games' for cat, count in zip(category_counts.index, category_counts.values)]
    ax.legend(legend_labels, loc='upper left', bbox_to_anchor=(1, 0, 0.3, 1), framealpha=0.9)
    
    ax.set_title('Prediction Outcomes by Confidence', fontsize=13, fontweight='bold', pad=15)

def plot_probability_distribution(predictions, ax):
    """Show distribution of predicted probabilities."""
    # Separate correct and incorrect predictions
    correct_probs = predictions.loc[predictions['correct'], 'home_win_probability']
    incorrect_probs = predictions.loc[~predictions['correct'], 'home_win_probability']
    
    # Create histogram
    bins = np.linspace(0.5, 1.0, 26)
    ax.hist(correct_probs, bins=bins, alpha=0.6, label='Correct Predictions', 
           color='#2ecc71', edgecolor='black', linewidth=0.5)
    ax.hist(incorrect_probs, bins=bins, alpha=0.6, label='Incorrect Predictions', 
           color='#e74c3c', edgecolor='black', linewidth=0.5)
    
    # Add mean lines
    ax.axvline(correct_probs.mean(), color='#27ae60', linestyle='--', 
              linewidth=2, label=f'Correct Mean: {correct_probs.mean():.3f}')
    ax.axvline(incorrect_probs.mean(), color='#c0392b', linestyle='--', 
              linewidth=2, label=f'Incorrect Mean: {incorrect_probs.mean():.3f}')
    
    ax.set_xlabel('Predicted Probability (Home Win)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Number of Games', fontsize=11, fontweight='bold')
    ax.set_title('Distribution of Model Confidence', fontsize=13, fontweight='bold', pad=15)
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(axis='y', alpha=0.3)

def plot_accuracy_by_probability(predictions, ax):
    """Show accuracy as function of predicted probability."""
    # Create fine bins for smooth curve
    prob_bins = np.linspace(0.5, 1.0, 21)
    bin_centers = (prob_bins[:-1] + prob_bins[1:]) / 2
    
    accuracies = []
    counts = []
    
    for i in range(len(prob_bins) - 1):
        mask = (predictions['home_win_probability'] >= prob_bins[i]) & \
               (predictions['home_win_probability'] < prob_bins[i + 1])
        if i == len(prob_bins) - 2:  # Include upper bound in last bin
            mask = mask | (predictions['home_win_probability'] == 1.0)
        
        if mask.sum() >= 5:  # Only include bins with at least 5 games
            accuracies.append(predictions.loc[mask, 'correct'].mean() * 100)
            counts.append(mask.sum())
        else:
            accuracies.append(np.nan)
            counts.append(0)
    
    # Plot line
    valid_mask = ~np.isnan(accuracies)
    ax.plot(bin_centers[valid_mask], np.array(accuracies)[valid_mask], 
           'o-', linewidth=2.5, markersize=8, color='#3498db', 
           markeredgecolor='black', markeredgewidth=1)
    
    # Add reference line
    overall_accuracy = predictions['correct'].mean() * 100
    ax.axhline(y=overall_accuracy, color='green', linestyle='--', 
              linewidth=2, label=f'Overall Accuracy: {overall_accuracy:.1f}%', alpha=0.7)
    ax.axhline(y=50, color='red', linestyle='--', linewidth=1, 
              label='Random Guessing: 50%', alpha=0.5)
    
    # Shade uncertainty region
    ax.fill_between(bin_centers, 45, 55, alpha=0.1, color='red')
    
    ax.set_xlabel('Predicted Probability (Home Win)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Model Accuracy (%)', fontsize=11, fontweight='bold')
    ax.set_title('Accuracy vs Model Confidence', fontsize=13, fontweight='bold', pad=15)
    ax.legend(loc='lower right', framealpha=0.9)
    ax.grid(alpha=0.3)
    ax.set_ylim(0, 100)

def plot_error_patterns(predictions, ax):
    """Analyze patterns in incorrect predictions."""
    # Create categories for analysis
    incorrect = predictions[~predictions['correct']].copy()
    
    # Categorize by scenario
    def categorize_error(row):
        prob = row['home_win_probability']
        home_win = row['home_win']
        
        if home_win == 1:
            # Model predicted away win, but home won (false negative)
            if prob < 0.55:
                return 'Strong Wrong (FN)'
            else:
                return 'Close Call (FN)'
        else:
            # Model predicted home win, but away won (false positive)
            if prob >= 0.65:
                return 'Strong Wrong (FP)'
            else:
                return 'Close Call (FP)'
    
    incorrect['error_type'] = incorrect.apply(categorize_error, axis=1)
    
    # Count errors by type
    error_counts = incorrect['error_type'].value_counts().sort_index()
    
    # Create bar plot
    colors_map = {
        'Strong Wrong (FP)': '#e74c3c',
        'Close Call (FP)': '#e67e22',
        'Strong Wrong (FN)': '#c0392b',
        'Close Call (FN)': '#d35400'
    }
    colors = [colors_map.get(x, '#95a5a6') for x in error_counts.index]
    
    bars = ax.bar(range(len(error_counts)), error_counts.values, color=colors, 
                  edgecolor='black', linewidth=1.5, alpha=0.8)
    
    # Add value labels
    for i, (bar, val) in enumerate(zip(bars, error_counts.values)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val}\n({val/len(incorrect)*100:.1f}%)',
               ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax.set_xlabel('Error Type', fontsize=11, fontweight='bold')
    ax.set_ylabel('Number of Errors', fontsize=11, fontweight='bold')
    ax.set_title('Error Analysis by Type', fontsize=13, fontweight='bold', pad=15)
    ax.set_xticks(range(len(error_counts)))
    ax.set_xticklabels(error_counts.index, rotation=15, ha='right')
    ax.grid(axis='y', alpha=0.3)
    
    # Add subtitle
    total_errors = len(incorrect)
    total_games = len(predictions)
    ax.text(0.5, -0.15, f'Total Errors: {total_errors} of {total_games} games ({total_errors/total_games*100:.1f}%)',
           ha='center', transform=ax.transAxes, fontsize=9, style='italic', color='gray')

def create_prediction_analysis():
    """Create comprehensive prediction analysis visualization."""
    print("Loading prediction data...")
    predictions = load_predictions()
    predictions = create_confidence_bins(predictions)
    
    print(f"Analyzing {len(predictions)} games...")
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.35)
    
    # Create axes
    ax1 = fig.add_subplot(gs[0, :2])   # Win rate by confidence (wide)
    ax2 = fig.add_subplot(gs[0, 2])    # Error pie chart
    ax3 = fig.add_subplot(gs[1, 0])    # Calibration curve
    ax4 = fig.add_subplot(gs[1, 1])    # Probability distribution
    ax5 = fig.add_subplot(gs[1, 2])    # Accuracy by probability
    ax6 = fig.add_subplot(gs[2, :])    # Error patterns (wide)
    
    # Generate plots
    print("Generating visualizations...")
    plot_win_rate_by_confidence(predictions, ax1)
    plot_error_analysis(predictions, ax2)
    plot_calibration_bins(predictions, ax3)
    plot_probability_distribution(predictions, ax4)
    plot_accuracy_by_probability(predictions, ax5)
    plot_error_patterns(predictions, ax6)
    
    # Add main title
    overall_accuracy = predictions['correct'].mean() * 100
    fig.suptitle(
        f'NHL Prediction Model - Comprehensive Analysis (2023-24 Season)\n'
        f'Overall Accuracy: {overall_accuracy:.2f}% | Total Games: {len(predictions)}',
        fontsize=16, fontweight='bold', y=0.995
    )
    
    # Save
    output_path = Path('reports/prediction_analysis.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Visualization saved to: {output_path}")
    
    # Print summary statistics
    print("\n" + "="*70)
    print("PREDICTION ANALYSIS SUMMARY")
    print("="*70)
    
    print(f"\nOverall Performance:")
    print(f"  Total Games: {len(predictions)}")
    print(f"  Correct Predictions: {predictions['correct'].sum()}")
    print(f"  Accuracy: {overall_accuracy:.2f}%")
    
    print(f"\nBy Confidence Level:")
    conf_summary = predictions.groupby('confidence_bin', observed=True).agg({
        'correct': ['mean', 'count']
    })
    for idx, row in conf_summary.iterrows():
        acc = row[('correct', 'mean')] * 100
        count = int(row[('correct', 'count')])
        print(f"  {idx}: {acc:.1f}% accuracy ({count} games)")
    
    high_conf = predictions[predictions['home_win_probability'] >= 0.65]
    print(f"\nHigh Confidence Predictions (≥65%):")
    print(f"  Games: {len(high_conf)}")
    print(f"  Accuracy: {high_conf['correct'].mean()*100:.2f}%")
    
    close_calls = predictions[(predictions['home_win_probability'] >= 0.5) & 
                              (predictions['home_win_probability'] < 0.55)]
    print(f"\nClose Calls (50-55%):")
    print(f"  Games: {len(close_calls)}")
    print(f"  Accuracy: {close_calls['correct'].mean()*100:.2f}%")
    
    print("\n" + "="*70)
    
    plt.show()

if __name__ == "__main__":
    create_prediction_analysis()


