import type { MatchPrediction } from '../api/types';

interface MatchCardProps {
  prediction: MatchPrediction;
}

export function MatchCard({ prediction: p }: MatchCardProps) {
  const maxProb = Math.max(p.home_win_prob, p.draw_prob, p.away_win_prob);
  const outcome =
    maxProb === p.home_win_prob ? p.home_team
    : maxProb === p.away_win_prob ? p.away_team
    : 'Draw';

  return (
    <div className="match-card">
      <div className="match-teams">
        <div className={`team-side ${outcome === p.home_team ? 'is-winner' : ''}`}>
          <span className="team-label">{p.home_team}</span>
          <span className="prob-value">{(p.home_win_prob * 100).toFixed(0)}%</span>
        </div>
        <div className="match-divider">
          <span className="vs-text">VS</span>
        </div>
        <div className={`team-side ${outcome === p.away_team ? 'is-winner' : ''}`}>
          <span className="prob-value">{(p.away_win_prob * 100).toFixed(0)}%</span>
          <span className="team-label">{p.away_team}</span>
        </div>
      </div>
      <div className="prob-bar-full">
        <div className="prob-segment home" style={{ width: `${p.home_win_prob * 100}%` }} />
        <div className="prob-segment draw" style={{ width: `${p.draw_prob * 100}%` }} />
        <div className="prob-segment away" style={{ width: `${p.away_win_prob * 100}%` }} />
      </div>
      <div className="match-footer">
        <span className="predicted-winner">
          {outcome} {outcome === 'Draw' ? '' : 'favored'}
        </span>
        <span className="confidence">
          {(maxProb * 100).toFixed(0)}% confidence
        </span>
      </div>
    </div>
  );
}
