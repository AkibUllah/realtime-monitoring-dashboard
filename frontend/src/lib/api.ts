import type { AlertRule } from './types';

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

export function wsUrl(): string {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined;
  if (explicit) return explicit;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/ws/metrics`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  rules: () => request<AlertRule[]>('/api/alerts/rules'),
  toggleRule: (id: number, enabled: boolean) =>
    request<AlertRule>(`/api/alerts/rules/${id}`, { method: 'PATCH', body: JSON.stringify({ enabled }) }),
};
