import React, { useState, useEffect } from 'react';
import './FootballMatchPredictor.css';

const FootballMatchPredictor = () => {
  const [homeTeam, setHomeTeam] = useState('');
  const [awayTeam, setAwayTeam] = useState('');
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);
  const [teams, setTeams] = useState([]);
  const [historyMatches, setHistoryMatches] = useState([]);

  // Fetch available teams on component mount
  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      const response = await fetch('/api/teams');
      const data = await response.json();
      setTeams(data.teams || []);
    } catch (err) {
      console.error('Failed to fetch teams:', err);
    }
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    
    if (!homeTeam || !awayTeam) {
      setError('Please select both teams');
      return;
    }

    if (homeTeam === awayTeam) {
      setError('Please select different teams');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          home_team: homeTeam,
          away_team: awayTeam,
        }),
      });

      if (!response.ok) {
        throw new Error('Prediction failed');
      }

      const data = await response.json();
      setPrediction(data);
      
      // Add to history
      setHistoryMatches(prev => [{
        home: homeTeam,
        away: awayTeam,
        prediction: data,
        timestamp: new Date()
      }, ...prev.slice(0, 9)]);
      
    } catch (err) {
      setError(err.message || 'Failed to get prediction');
    } finally {
      setLoading(false);
    }
  };

  const getPredictionColor = (confidence) => {
    if (confidence >= 70) return '#10b981'; // green
    if (confidence >= 50) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  const formatConfidence = (value) => {
    if (typeof value === 'string') {
      const match = value.match(/[\d.]+/);
      return match ? parseFloat(match[0]).toFixed(1) : '0';
    }
    return parseFloat(value).toFixed(1);
  };

  return (
    <div className="football-predictor">
      <div className="predictor-container">
        {/* Header */}
        <div className="predictor-header">
          <h1>⚽ Football Match Predictor</h1>
          <p>AI-powered predictions using Bayesian analysis</p>
        </div>

        {/* Main Prediction Form */}
        <form onSubmit={handlePredict} className="prediction-form">
          <div className="form-group team-selector">
            <div className="input-group">
              <label htmlFor="home-team">Home Team</label>
              <select
                id="home-team"
                value={homeTeam}
                onChange={(e) => setHomeTeam(e.target.value)}
                className="team-input"
              >
                <option value="">Select Home Team</option>
                {teams.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            </div>

            <div className="vs-divider">VS</div>

            <div className="input-group">
              <label htmlFor="away-team">Away Team</label>
              <select
                id="away-team"
                value={awayTeam}
                onChange={(e) => setAwayTeam(e.target.value)}
                className="team-input"
              >
                <option value="">Select Away Team</option>
                {teams.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="predict-button"
          >
            {loading ? 'Analyzing Match...' : 'Get Prediction'}
          </button>
        </form>

        {/* Prediction Results */}
        {prediction && (
          <div className="prediction-results">
            <h2>Match Analysis</h2>

            {/* Match Info */}
            <div className="match-info">
              <div className="team-card home">
                <h3>{homeTeam}</h3>
                <div className="elo-badge">
                  Elo: {prediction.home_elo || 'N/A'}
                </div>
              </div>

              <div className="match-stats">
                <div className="score-prediction">
                  <h4>Expected Score</h4>
                  <div className="score-display">
                    {prediction.expected_goals_home || 0} - {prediction.expected_goals_away || 0}
                  </div>
                </div>
              </div>

              <div className="team-card away">
                <h3>{awayTeam}</h3>
                <div className="elo-badge">
                  Elo: {prediction.away_elo || 'N/A'}
                </div>
              </div>
            </div>

            {/* Predictions Grid */}
            <div className="predictions-grid">
              {/* Match Result */}
              <div className="prediction-card">
                <h4>Match Result</h4>
                <div className="prediction-options">
                  {prediction.home_win && (
                    <div className="option-item">
                      <span className="option-label">Home Win</span>
                      <div
                        className="confidence-bar"
                        style={{
                          background: getPredictionColor(
                            formatConfidence(prediction.home_win)
                          ),
                        }}
                      >
                        {formatConfidence(prediction.home_win)}%
                      </div>
                    </div>
                  )}
                  {prediction.draw && (
                    <div className="option-item">
                      <span className="option-label">Draw</span>
                      <div
                        className="confidence-bar"
                        style={{
                          background: getPredictionColor(
                            formatConfidence(prediction.draw)
                          ),
                        }}
                      >
                        {formatConfidence(prediction.draw)}%
                      </div>
                    </div>
                  )}
                  {prediction.away_win && (
                    <div className="option-item">
                      <span className="option-label">Away Win</span>
                      <div
                        className="confidence-bar"
                        style={{
                          background: getPredictionColor(
                            formatConfidence(prediction.away_win)
                          ),
                        }}
                      >
                        {formatConfidence(prediction.away_win)}%
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Goals Predictions */}
              <div className="prediction-card">
                <h4>Total Goals</h4>
                <div className="prediction-options">
                  {prediction['Over 1.5 Goals'] && (
                    <div className="option-item">
                      <span className="option-label">Over 1.5</span>
                      <span className="prediction-value">
                        {prediction['Over 1.5 Goals']}
                      </span>
                    </div>
                  )}
                  {prediction['Over 2.5 Goals'] && (
                    <div className="option-item">
                      <span className="option-label">Over 2.5</span>
                      <span className="prediction-value">
                        {prediction['Over 2.5 Goals']}
                      </span>
                    </div>
                  )}
                  {prediction['Over 3.5 Goals'] && (
                    <div className="option-item">
                      <span className="option-label">Over 3.5</span>
                      <span className="prediction-value">
                        {prediction['Over 3.5 Goals']}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Both Teams To Score */}
              {prediction['Both Teams To Score'] && (
                <div className="prediction-card">
                  <h4>Both Teams to Score</h4>
                  <div className="btts-result">
                    <span className="btts-value">
                      {prediction['Both Teams To Score']}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Team Stats */}
            {prediction.team_stats && (
              <div className="team-stats">
                <h3>Team Statistics</h3>
                <div className="stats-grid">
                  {prediction.team_stats.home && (
                    <div className="stat-block">
                      <h5>{homeTeam}</h5>
                      <ul>
                        <li>
                          <span>Recent Form:</span>
                          {prediction.team_stats.home.recent_form}
                        </li>
                        <li>
                          <span>Avg Goals:</span>
                          {prediction.team_stats.home.avg_goals}
                        </li>
                        <li>
                          <span>Win Rate:</span>
                          {prediction.team_stats.home.win_rate}%
                        </li>
                      </ul>
                    </div>
                  )}
                  {prediction.team_stats.away && (
                    <div className="stat-block">
                      <h5>{awayTeam}</h5>
                      <ul>
                        <li>
                          <span>Recent Form:</span>
                          {prediction.team_stats.away.recent_form}
                        </li>
                        <li>
                          <span>Avg Goals:</span>
                          {prediction.team_stats.away.avg_goals}
                        </li>
                        <li>
                          <span>Win Rate:</span>
                          {prediction.team_stats.away.win_rate}%
                        </li>
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* History Section */}
        {historyMatches.length > 0 && (
          <div className="history-section">
            <h3>Recent Predictions</h3>
            <div className="history-list">
              {historyMatches.map((match, idx) => (
                <div key={idx} className="history-item">
                  <div className="history-teams">
                    {match.home} vs {match.away}
                  </div>
                  <div className="history-prediction">
                    {match.prediction.home_win && (
                      <span className="history-badge">
                        {formatConfidence(match.prediction.home_win)}% H Win
                      </span>
                    )}
                  </div>
                  <div className="history-time">
                    {new Date(match.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FootballMatchPredictor;
