import { useState, useEffect } from 'react';
import { KnockoutBracket } from '../components/KnockoutBracket';
import { ChampionBar } from '../components/ChampionBar';
import { SkeletonBracket, SkeletonChampionBar, StaggerIn } from '../components/Skeletons';
import { api } from '../api/client';
import type { MatchPrediction, TeamProbability } from '../api/types';

const GROUPS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'];

export function KnockoutPage() {
  const [predictions, setPredictions] = useState<MatchPrediction[]>([]);
  const [championProbs, setChampionProbs] = useState<TeamProbability[]>([]);
  const [teamGroups, setTeamGroups] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.predictions(),
      api.tournamentPrediction().catch(() => null),
    ]).then(([preds, sim]) => {
      setPredictions(preds);

      const tg: Record<string, string> = {};
      preds.forEach((p) => {
        const low = p.match_id % 1000;
        if (low > 72) return;
        const gi = Math.floor((low - 1) / 6);
        if (gi >= 0 && gi < 12) {
          if (!tg[p.home_team]) tg[p.home_team] = GROUPS[gi];
          if (!tg[p.away_team]) tg[p.away_team] = GROUPS[gi];
        }
      });
      setTeamGroups(tg);

      if (sim?.champion_probabilities) {
        setChampionProbs(sim.champion_probabilities);
      }

      setLoading(false);
    });
  }, []);

  return (
    <div className="knockout-page">
      <div className="page-header">
        <h1 className="page-title">Knockout Stage</h1>
        <p className="page-subtitle">32 teams · bracket simulation · champion odds</p>
      </div>

      {loading ? (
        <>
          <SkeletonBracket />
          <SkeletonChampionBar />
        </>
      ) : (
        <>
          <StaggerIn index={0}>
            <KnockoutBracket predictions={predictions} />
          </StaggerIn>

          {championProbs.length > 0 && (
            <StaggerIn index={1}>
              <ChampionBar data={championProbs} />
            </StaggerIn>
          )}

          <StaggerIn index={2}>
            <div className="team-group-list">
              <h2>Team Groups</h2>
              <div className="team-group-grid">
                {Object.entries(teamGroups).map(([team, group]) => (
                  <div key={team} className="team-group-chip">
                    <span className="chip-team">{team}</span>
                    <span className="chip-group">Group {group}</span>
                  </div>
                ))}
              </div>
            </div>
          </StaggerIn>
        </>
      )}
    </div>
  );
}
