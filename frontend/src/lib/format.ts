import type { Metric } from './types';

export const METRIC_LABEL: Record<Metric, string> = {
  cpu: 'CPU',
  memory: 'Memory',
  disk: 'Disk',
  net_rx: 'Net in',
  net_tx: 'Net out',
};

export function formatValue(metric: Metric, value: number): string {
  if (metric === 'net_rx' || metric === 'net_tx') return formatKbps(value);
  return `${value.toFixed(value >= 100 ? 0 : 1)}%`;
}

export function formatKbps(kbps: number): string {
  if (kbps >= 1_000_000) return `${(kbps / 1_000_000).toFixed(2)} Gbps`;
  if (kbps >= 1000) return `${(kbps / 1000).toFixed(1)} Mbps`;
  return `${Math.round(kbps)} kbps`;
}

export function formatClock(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleTimeString('en-GB', { hour12: false });
}

export function formatRelative(unixSeconds: number, now: number): string {
  const diff = Math.max(0, Math.round(now - unixSeconds));
  if (diff < 5) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}
