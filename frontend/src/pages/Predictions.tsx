import { useState, useEffect } from 'react';
import { MatchCard } from '../components/MatchCard';
import { SkeletonMatchCard, StaggerIn } from '../components/Skeletons';
import { api } from '../api/client';
import type { MatchPrediction } from '../api/types';

const FILTERS = [
  { key: 'all' as const, label: 'All Matches' },
  { key: 'home' as const, label: 'Home Win' },
  { key: 'away' as const, label: 'Away Win' },
  { key: 'draw' as const, label: 'Draw' },
];

export function PredictionsPage() {
  const [predictions, setPredictions] = useState<MatchPrediction[]>([]);
  const [filter, setFilter] = useState<'all' | 'home' | 'away' | 'draw'>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.predictions().then((preds) => {
      setPredictions(preds);
      setLoading(false);
    });
  }, []);

  const filtered = predictions.filter((p) => {
    const max = Math.max(p.home_win_prob, p.draw_prob, p.away_win_prob);
    if (filter === 'home') return max === p.home_win_prob;
    if (filter === 'away') return max === p.away_win_prob;
    if (filter === 'draw') return max === p.draw_prob;
    return true;
  });

  return (
    <div className="predictions-page">
      <div className="page-header">
        <h1 className="page-title">Match Predictions</h1>
        <p className="page-subtitle">{predictions.length || '...'} matches · XGBoost tuned model</p>
      </div>

      {!loading && (
        <div className="filter-bar">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`filter-btn ${filter === f.key ? 'active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="predictions-grid">
          {Array.from({ length: 12 }).map((_, i) => (
            <SkeletonMatchCard key={i} />
          ))}
        </div>
      ) : (
        <div className="predictions-grid">
          {filtered.map((p, i) => (
            <StaggerIn key={p.match_id} index={i}>
              <MatchCard prediction={p} />
            </StaggerIn>
          ))}
        </div>
      )}
    </div>
  );
}
