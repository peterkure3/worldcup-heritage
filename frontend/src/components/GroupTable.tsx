import type { GroupInfo, MatchPrediction } from '../api/types';

interface GroupTableProps {
  group: GroupInfo;
  predictions: MatchPrediction[];
}

export function GroupTable({ group, predictions }: GroupTableProps) {
  const sorted = [...group.standings].sort((a, b) => b.points - a.points || b.goal_diff - a.goal_diff || b.goals_for - a.goals_for);

  return (
    <div className="group-card">
      <div className="group-header">
        <span className="group-badge">Group {group.name}</span>
      </div>
      <div className="group-body">
        <table className="standings-table">
          <thead>
            <tr>
              <th className="col-pos">#</th>
              <th className="col-team">Team</th>
              <th className="col-stat">P</th>
              <th className="col-stat">W</th>
              <th className="col-stat">D</th>
              <th className="col-stat">L</th>
              <th className="col-stat">GF</th>
              <th className="col-stat">GA</th>
              <th className="col-stat">GD</th>
              <th className="col-pts">Pts</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((t, i) => (
              <tr key={t.team_id} className={i < 2 ? 'qualify' : ''}>
                <td className="col-pos">{i + 1}</td>
                <td className="col-team">
                  <img
                    className="team-flag"
                    src={t.flag_svg}
                    alt=""
                    width="20"
                    height="15"
                    loading="lazy"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                  <span className="team-name">{t.team_name}</span>
                </td>
                <td className="col-stat">{t.played}</td>
                <td className="col-stat">{t.won}</td>
                <td className="col-stat">{t.drawn}</td>
                <td className="col-stat">{t.lost}</td>
                <td className="col-stat">{t.goals_for}</td>
                <td className="col-stat">{t.goals_against}</td>
                <td className={`col-stat ${t.goal_diff > 0 ? 'pos' : t.goal_diff < 0 ? 'neg' : ''}`}>
                  {t.goal_diff > 0 ? `+${t.goal_diff}` : t.goal_diff}
                </td>
                <td className="col-pts"><span className="pts-badge">{t.points}</span></td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="group-matches">
          <div className="matches-label">Fixtures</div>
          {predictions.map((m) => {
            const maxProb = Math.max(m.home_win_prob, m.draw_prob, m.away_win_prob);
            const pred = maxProb === m.home_win_prob ? m.home_team : maxProb === m.away_win_prob ? m.away_team : 'Draw';
            return (
              <div key={m.match_id} className="mini-match">
                <div className="mini-teams">
                  <span className={pred === m.home_team ? 'winner' : ''}>{m.home_team}</span>
                  <span className="mini-vs">vs</span>
                  <span className={pred === m.away_team ? 'winner' : ''}>{m.away_team}</span>
                </div>
                <div className="mini-probs">
                  <span className="prob-bar home" style={{ width: `${m.home_win_prob * 100}%` }} />
                  <span className="prob-bar draw" style={{ width: `${m.draw_prob * 100}%` }} />
                  <span className="prob-bar away" style={{ width: `${m.away_win_prob * 100}%` }} />
                </div>
                <div className="mini-pred">
                  <span>{pred} wins</span>
                  <span className="mini-confidence">{(maxProb * 100).toFixed(0)}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
