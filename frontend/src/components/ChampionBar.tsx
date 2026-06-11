import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { TeamProbability } from '../api/types';

interface ChampionBarProps {
  data: TeamProbability[];
}

const GOLD = '#fbbf24';
const MUTED = '#64748b';

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{d.team}</strong>
      <div>Champion: {(d.champion_prob * 100).toFixed(1)}%</div>
      <div>Final: {(d.final_prob * 100).toFixed(1)}%</div>
      <div>Semi: {(d.semi_prob * 100).toFixed(1)}%</div>
    </div>
  );
}

export function ChampionBar({ data }: ChampionBarProps) {
  const sorted = [...data].sort((a, b) => b.champion_prob - a.champion_prob);
  const top = sorted.slice(0, 16);

  return (
    <div className="champion-section">
      <h2 className="champion-title">Champion Probabilities</h2>
      <p className="champion-subtitle">Top 16 contenders by championship probability</p>
      <ResponsiveContainer width="100%" height={Math.max(300, top.length * 32)}>
        <BarChart data={top} layout="vertical" margin={{ left: 100, right: 60, top: 8, bottom: 8 }}>
          <XAxis type="number" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} stroke={MUTED} />
          <YAxis type="category" dataKey="team" width={100} stroke={MUTED} tick={{ fontSize: 12 }} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="champion_prob" radius={[0, 4, 4, 0]}>
            {top.map((_, i) => (
              <Cell key={i} fill={i < 3 ? GOLD : i < 8 ? '#f59e0b' : '#78716c'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
