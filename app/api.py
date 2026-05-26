"""
Flask API for Football Match Predictions
Integrates with Bayesian predictor and provides REST endpoints
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import joblib
import logging
from datetime import datetime
from typing import Dict, Any, Tuple

# Import prediction modules
from footy.predictor_utils import create_bayesian_predictor
from footy.model_training import BayesianFootballPredictor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app initialization
app = Flask(__name__)
CORS(app)

# Global prediction system
prediction_system = {
    'predictor': None,
    'data': None,
    'teams': None,
    'is_ready': False,
    'last_updated': None
}


def initialize_prediction_system():
    """Initialize the prediction system with trained models"""
    try:
        logger.info("🚀 Initializing prediction system...")
        
        # Load processed data
        data_path = Path('data/processed/enhanced_bayesian_data.pkl')
        if not data_path.exists():
            logger.warning("Processed data not found. Running main.py first...")
            return False
        
        logger.info("📊 Loading processed data...")
        df_data = pd.read_pickle(data_path)
        prediction_system['data'] = df_data
        
        # Load or train models
        models_path = Path('models/football_models.joblib')
        if models_path.exists():
            logger.info("🤖 Loading trained models...")
            predictor = joblib.load(models_path)
        else:
            logger.info("🤖 Training models (first time)...")
            predictor = BayesianFootballPredictor()
            predictor.train_models(df_data)
            models_path.parent.mkdir(exist_ok=True)
            joblib.dump(predictor, models_path)
            logger.info(f"✅ Models saved to {models_path}")
        
        # Create match predictor
        logger.info("🧠 Creating Bayesian match predictor...")
        match_predictor = create_bayesian_predictor(df_data, models_path)
        prediction_system['predictor'] = match_predictor
        
        # Extract teams
        teams = sorted(set(df_data['HomeTeam'].unique()) | set(df_data['AwayTeam'].unique()))
        prediction_system['teams'] = teams
        
        prediction_system['is_ready'] = True
        prediction_system['last_updated'] = datetime.now()
        
        logger.info(f"✅ Prediction system initialized with {len(teams)} teams")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize prediction system: {e}")
        import traceback
        traceback.print_exc()
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'prediction_ready': prediction_system['is_ready'],
        'last_updated': prediction_system['last_updated'].isoformat() if prediction_system['last_updated'] else None
    })


@app.route('/api/teams', methods=['GET'])
def get_teams():
    """Get list of available teams"""
    if not prediction_system['is_ready']:
        return jsonify({'error': 'Prediction system not initialized'}), 503
    
    return jsonify({
        'teams': prediction_system['teams'],
        'count': len(prediction_system['teams'])
    })


@app.route('/api/predict', methods=['POST'])
def predict_match():
    """
    Predict a football match
    
    Request JSON:
    {
        "home_team": "Arsenal",
        "away_team": "Chelsea"
    }
    
    Response JSON:
    {
        "match": "Arsenal vs Chelsea",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "predictions": {
            "Match Outcome": "Home Win",
            "Over 1.5 Goals": "Yes",
            "Over 2.5 Goals": "Yes",
            "Over 3.5 Goals": "No",
            "Both Teams to Score": "Yes",
            "Total Goals": 2.5
        },
        "probabilities": {
            "Match Outcome": {
                "Home Win": "65%",
                "Draw": "20%",
                "Away Win": "15%"
            }
        },
        "team_stats": {
            "home": {...},
            "away": {...}
        },
        "home_elo": 1650,
        "away_elo": 1480,
        "expected_goals_home": 1.8,
        "expected_goals_away": 0.9,
        "confidence_score": 0.87,
        "timestamp": "2026-05-26T10:30:00"
    }
    """
    try:
        if not prediction_system['is_ready']:
            return jsonify({'error': 'Prediction system not initialized'}), 503
        
        # Parse request
        data = request.get_json()
        home_team = data.get('home_team', '').strip()
        away_team = data.get('away_team', '').strip()
        
        # Validate input
        if not home_team or not away_team:
            return jsonify({'error': 'home_team and away_team required'}), 400
        
        if home_team == away_team:
            return jsonify({'error': 'home_team and away_team must be different'}), 400
        
        # Check if teams exist
        available_teams = prediction_system['teams']
        if home_team not in available_teams:
            return jsonify({'error': f'Team "{home_team}" not found'}), 404
        if away_team not in available_teams:
            return jsonify({'error': f'Team "{away_team}" not found'}), 404
        
        logger.info(f"🔮 Predicting: {home_team} vs {away_team}")
        
        # Get prediction
        predictor = prediction_system['predictor']
        bayesian_analysis = predictor.predict_with_full_bayesian_analysis(home_team, away_team)
        
        # Extract prediction data
        predictions = bayesian_analysis.get('predictions', {})
        probabilities = bayesian_analysis.get('probabilities', {})
        confidence_intervals = bayesian_analysis.get('confidence_intervals', {})
        poisson_analysis = bayesian_analysis.get('poisson_analysis', {})
        team_stats = bayesian_analysis.get('team_stats', {})
        
        # Get Elo ratings
        home_elo = bayesian_analysis.get('home_elo', 'N/A')
        away_elo = bayesian_analysis.get('away_elo', 'N/A')
        
        # Get expected goals
        expected_goals = poisson_analysis.get('expected_goals', {})
        expected_goals_home = expected_goals.get('home', 'N/A')
        expected_goals_away = expected_goals.get('away', 'N/A')
        
        # Calculate confidence score
        confidence_score = calculate_confidence_score(predictions, probabilities)
        
        # Build response
        response = {
            'match': f"{home_team} vs {away_team}",
            'home_team': home_team,
            'away_team': away_team,
            'predictions': predictions,
            'probabilities': probabilities,
            'confidence_intervals': confidence_intervals,
            'team_stats': team_stats,
            'home_elo': home_elo,
            'away_elo': away_elo,
            'expected_goals_home': expected_goals_home,
            'expected_goals_away': expected_goals_away,
            'confidence_score': round(confidence_score, 3),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add Poisson analysis if available
        if poisson_analysis:
            response['poisson_analysis'] = {
                'most_likely_scorelines': poisson_analysis.get('most_likely_scorelines', [])[:5],
                'expected_goals': expected_goals
            }
        
        logger.info(f"✅ Prediction successful for {home_team} vs {away_team}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ Prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/batch-predict', methods=['POST'])
def batch_predict():
    """
    Batch predict multiple matches
    
    Request JSON:
    {
        "matches": [
            {"home_team": "Arsenal", "away_team": "Chelsea"},
            {"home_team": "Man City", "away_team": "Liverpool"}
        ]
    }
    """
    try:
        if not prediction_system['is_ready']:
            return jsonify({'error': 'Prediction system not initialized'}), 503
        
        data = request.get_json()
        matches = data.get('matches', [])
        
        if not matches:
            return jsonify({'error': 'matches array required'}), 400
        
        results = []
        errors = []
        
        for i, match in enumerate(matches):
            try:
                home_team = match.get('home_team', '').strip()
                away_team = match.get('away_team', '').strip()
                
                if not home_team or not away_team:
                    errors.append(f"Match {i}: Missing home_team or away_team")
                    continue
                
                # Simulate single prediction request
                predictor = prediction_system['predictor']
                bayesian_analysis = predictor.predict_with_full_bayesian_analysis(home_team, away_team)
                
                results.append({
                    'match': f"{home_team} vs {away_team}",
                    'status': 'success',
                    'prediction': bayesian_analysis.get('predictions', {})
                })
            except Exception as e:
                errors.append(f"Match {i} ({home_team} vs {away_team}): {str(e)}")
        
        return jsonify({
            'total': len(matches),
            'successful': len(results),
            'failed': len(errors),
            'results': results,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"❌ Batch prediction failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/team-stats/<team_name>', methods=['GET'])
def get_team_stats(team_name):
    """Get statistics for a specific team"""
    try:
        if not prediction_system['is_ready']:
            return jsonify({'error': 'Prediction system not initialized'}), 503
        
        df = prediction_system['data']
        
        # Get team data
        home_matches = df[df['HomeTeam'] == team_name]
        away_matches = df[df['AwayTeam'] == team_name]
        
        if len(home_matches) == 0 and len(away_matches) == 0:
            return jsonify({'error': f'Team "{team_name}" not found'}), 404
        
        # Calculate stats
        stats = calculate_team_statistics(df, team_name)
        
        return jsonify({
            'team': team_name,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get team stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/system-info', methods=['GET'])
def system_info():
    """Get system information"""
    try:
        predictor_ready = prediction_system['is_ready']
        teams_count = len(prediction_system['teams']) if prediction_system['teams'] else 0
        data_count = len(prediction_system['data']) if prediction_system['data'] is not None else 0
        
        return jsonify({
            'status': 'ready' if predictor_ready else 'not_ready',
            'teams_available': teams_count,
            'matches_in_database': data_count,
            'last_initialized': prediction_system['last_updated'].isoformat() if prediction_system['last_updated'] else None,
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def calculate_confidence_score(predictions: Dict, probabilities: Dict) -> float:
    """Calculate overall confidence score for predictions"""
    try:
        confidence_factors = []
        
        # Check if match outcome has probabilities
        if 'Match Outcome' in probabilities and isinstance(probabilities['Match Outcome'], dict):
            probs = probabilities['Match Outcome']
            max_prob = max(probs.values(), default=0)
            confidence_factors.append(max_prob)
        
        # Average confidence
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        return 0.5  # Default confidence
        
    except Exception as e:
        logger.warning(f"Could not calculate confidence score: {e}")
        return 0.5


def calculate_team_statistics(df: pd.DataFrame, team_name: str) -> Dict[str, Any]:
    """Calculate statistics for a team"""
    try:
        home_matches = df[df['HomeTeam'] == team_name]
        away_matches = df[df['AwayTeam'] == team_name]
        
        all_matches = len(home_matches) + len(away_matches)
        
        # Home stats
        home_wins = len(home_matches[home_matches['FTR'] == 'H'])
        home_draws = len(home_matches[home_matches['FTR'] == 'D'])
        home_losses = len(home_matches[home_matches['FTR'] == 'A'])
        home_goals_for = home_matches['FTHG'].sum() if len(home_matches) > 0 else 0
        home_goals_against = home_matches['FTAG'].sum() if len(home_matches) > 0 else 0
        
        # Away stats
        away_wins = len(away_matches[away_matches['FTR'] == 'A'])
        away_draws = len(away_matches[away_matches['FTR'] == 'D'])
        away_losses = len(away_matches[away_matches['FTR'] == 'H'])
        away_goals_for = away_matches['FTAG'].sum() if len(away_matches) > 0 else 0
        away_goals_against = away_matches['FTHG'].sum() if len(away_matches) > 0 else 0
        
        # Total stats
        total_wins = home_wins + away_wins
        total_draws = home_draws + away_draws
        total_losses = home_losses + away_losses
        total_goals_for = home_goals_for + away_goals_for
        total_goals_against = home_goals_against + away_goals_against
        
        return {
            'total_matches': all_matches,
            'home': {
                'matches': len(home_matches),
                'wins': home_wins,
                'draws': home_draws,
                'losses': home_losses,
                'goals_for': home_goals_for,
                'goals_against': home_goals_against,
                'win_rate': round(home_wins / len(home_matches) * 100, 2) if len(home_matches) > 0 else 0
            },
            'away': {
                'matches': len(away_matches),
                'wins': away_wins,
                'draws': away_draws,
                'losses': away_losses,
                'goals_for': away_goals_for,
                'goals_against': away_goals_against,
                'win_rate': round(away_wins / len(away_matches) * 100, 2) if len(away_matches) > 0 else 0
            },
            'overall': {
                'wins': total_wins,
                'draws': total_draws,
                'losses': total_losses,
                'goals_for': total_goals_for,
                'goals_against': total_goals_against,
                'goal_difference': total_goals_for - total_goals_against,
                'win_rate': round(total_wins / all_matches * 100, 2) if all_matches > 0 else 0,
                'avg_goals_per_match': round(total_goals_for / all_matches, 2) if all_matches > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Error calculating team stats: {e}")
        return {}


if __name__ == '__main__':
    print("🚀 Starting Football Prediction API Server...")
    print("=" * 60)
    
    # Initialize prediction system
    if initialize_prediction_system():
        print("✅ API ready!")
        print("📍 Server: http://localhost:5000")
        print("📚 API Docs: http://localhost:5000/api/teams")
        print("=" * 60)
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Failed to initialize prediction system")
        print("   Run 'python main.py' first to train models")
        sys.exit(1)
