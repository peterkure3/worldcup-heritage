import { useState, useEffect, useCallback } from 'react';
import { GroupTable } from '../components/GroupTable';
import { SkeletonGroupCard, StaggerIn } from '../components/Skeletons';
import { api } from '../api/client';
import { usePoll } from '../api/usePoll';
import type { GroupInfo, MatchPrediction } from '../api/types';

const GROUPS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'];

export function GroupsPage() {
  const [groups, setGroups] = useState<GroupInfo[]>([]);
  const [predictions, setPredictions] = useState<MatchPrediction[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(() => {
    Promise.all([
      api.groups(),
      api.predictions(),
    ]).then(([groupsData, preds]) => {
      setGroups(groupsData.groups);
      setPredictions(preds);
      setLoading(false);
    });
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  usePoll(fetchData, 30_000, !loading);

  return (
    <div className="groups-page">
      <div className="page-header">
        <h1 className="page-title">Group Stage</h1>
        <p className="page-subtitle">12 groups · 48 teams · XGBoost v1 tuned</p>
      </div>

      {loading ? (
        <div className="groups-grid">
          {Array.from({ length: 12 }).map((_, i) => (
            <SkeletonGroupCard key={i} />
          ))}
        </div>
      ) : (
        <div className="groups-grid">
          {groups.map((g, i) => {
            const groupIdx = GROUPS.indexOf(g.name);
            const groupPreds = predictions.filter((p) => {
              const low = p.match_id % 1000;
              if (low > 72) return false;
              const gi = Math.floor((low - 1) / 6);
              return gi === groupIdx;
            });
            return (
              <StaggerIn key={g.name} index={i}>
                <GroupTable group={g} predictions={groupPreds} />
              </StaggerIn>
            );
          })}
        </div>
      )}
    </div>
  );
}
