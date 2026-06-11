import type { MatchPrediction, TournamentSimulation, GroupsData } from './types';

const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export const api = {
  health: () => fetchJson<{ status: string }>('/api/health'),

  predictions: () => fetchJson<MatchPrediction[]>('/api/predictions'),

  matchPrediction: (id: number) =>
    fetchJson<MatchPrediction>(`/api/predictions/${id}`),

  tournamentPrediction: () =>
    fetchJson<TournamentSimulation>('/api/predictions/tournament'),

  groups: () => fetchJson<GroupsData>('/api/groups'),
};
