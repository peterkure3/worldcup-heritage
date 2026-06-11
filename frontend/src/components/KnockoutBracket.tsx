import type { MatchPrediction } from '../api/types';

interface KnockoutBracketProps {
  predictions: MatchPrediction[];
}

const ROUNDS = ['Last 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Final'];

export function KnockoutBracket({ predictions }: KnockoutBracketProps) {
  const knockout = predictions.filter((p) => {
    const low = p.match_id % 1000;
    return low >= 73;
  });

  if (knockout.length === 0) {
    return (
      <div className="bracket-empty">
        <h2>Knockout Stage - TBD</h2>
        <p>Knockout matchups depend on group stage results. Predictions will appear after group-stage simulation resolves bracket seeding.</p>
      </div>
    );
  }

  const rounds = ROUNDS.map((name, i) => {
    const perRound = 2 ** (ROUNDS.length - 1 - i);
    const matches = knockout.slice(
      knockout.length - perRound,
      knockout.length - perRound + perRound
    );
    return { name, matches };
  });

  return (
    <div className="bracket-container">
      <h2 className="bracket-title">Knockout Bracket</h2>
      <div className="bracket-grid">
        {rounds.map((round) => (
          <div key={round.name} className="bracket-round">
            <div className="round-label">{round.name}</div>
            {round.matches.map((m) => {
              const maxProb = Math.max(m.home_win_prob, m.draw_prob, m.away_win_prob);
              const winner = maxProb === m.home_win_prob ? m.home_team
                : maxProb === m.away_win_prob ? m.away_team : 'Draw';
              return (
                <div key={m.match_id} className="bracket-match">
                  <div className="bracket-team top">
                    <span>{m.home_team}</span>
                    <span className="bracket-prob">{(m.home_win_prob * 100).toFixed(0)}%</span>
                  </div>
                  <div className="bracket-team bottom">
                    <span>{m.away_team}</span>
                    <span className="bracket-prob">{(m.away_win_prob * 100).toFixed(0)}%</span>
                  </div>
                  {winner !== 'Draw' && (
                    <div className="bracket-winner">{winner} →</div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
