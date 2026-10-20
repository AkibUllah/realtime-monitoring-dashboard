import { METRICS, type AlertRule, type AlertStatus, type Metric, type NodeSnapshot, type Notification, type Point, type ServerMessage } from './types';

export interface MetricsState {
  nodes: Record<string, NodeSnapshot>;
  series: Record<string, Partial<Record<Metric, Point[]>>>;
  alerts: AlertStatus[];
  rules: AlertRule[];
  notifications: Notification[];
  lastTs: number | null;
  /** Oldest sample kept, in seconds. Ticks beyond this are trimmed. */
  retentionSeconds: number;
}

export const MAX_NOTIFICATIONS = 100;

export const initialMetricsState = (retentionSeconds = 3600): MetricsState => ({
  nodes: {},
  series: {},
  alerts: [],
  rules: [],
  notifications: [],
  lastTs: null,
  retentionSeconds,
});

export type MetricsAction =
  | { type: 'message'; message: ServerMessage }
  | { type: 'rules'; rules: AlertRule[] }
  | { type: 'reset' };

function trim(points: Point[], cutoff: number): Point[] {
  let i = 0;
  while (i < points.length && points[i][0] < cutoff) i++;
  return i === 0 ? points : points.slice(i);
}

function appendTick(series: MetricsState['series'], nodes: NodeSnapshot[], cutoff: number): MetricsState['series'] {
  const next: MetricsState['series'] = { ...series };
  for (const node of nodes) {
    const current = { ...(next[node.node_id] ?? {}) };
    for (const metric of METRICS) {
      const value = node.metrics[metric];
      if (value === undefined) continue;
      const existing = current[metric] ?? [];
      const last = existing[existing.length - 1];
      // ignore duplicate/out-of-order ticks (reconnect replays)
      if (last && node.ts <= last[0]) continue;
      current[metric] = trim([...existing, [node.ts, value]], cutoff);
    }
    next[node.node_id] = current;
  }
  return next;
}

function mergeNotifications(existing: Notification[], incoming: Notification[]): Notification[] {
  if (incoming.length === 0) return existing;
  const seen = new Set(existing.map((n) => n.id));
  const fresh = incoming.filter((n) => !seen.has(n.id));
  // newest first
  return [...fresh.sort((a, b) => b.id - a.id), ...existing].slice(0, MAX_NOTIFICATIONS);
}

export function metricsReducer(state: MetricsState, action: MetricsAction): MetricsState {
  switch (action.type) {
    case 'reset':
      return initialMetricsState(state.retentionSeconds);
    case 'rules':
      return { ...state, rules: action.rules };
    case 'message': {
      const msg = action.message;
      if (msg.type === 'pong') return state;
      const cutoff = msg.ts - state.retentionSeconds;
      const nodes = { ...state.nodes };
      for (const n of msg.nodes) nodes[n.node_id] = n;
      if (msg.type === 'snapshot') {
        // Server history is authoritative on (re)connect; it covers the gap we missed.
        const series: MetricsState['series'] = {};
        for (const [nodeId, metrics] of Object.entries(msg.history)) {
          series[nodeId] = {};
          for (const [metric, pts] of Object.entries(metrics) as [Metric, Point[]][]) {
            series[nodeId][metric] = trim(pts, cutoff);
          }
        }
        return {
          ...state,
          nodes,
          series: appendTick(series, msg.nodes, cutoff),
          alerts: msg.alerts,
          rules: msg.rules,
          notifications: [...msg.notifications].sort((a, b) => b.id - a.id).slice(0, MAX_NOTIFICATIONS),
          lastTs: msg.ts,
        };
      }
      return {
        ...state,
        nodes,
        series: appendTick(state.series, msg.nodes, cutoff),
        alerts: msg.alerts,
        notifications: mergeNotifications(state.notifications, msg.notifications),
        lastTs: msg.ts,
      };
    }
    default:
      return state;
  }
}

export interface TimeRange { label: string; seconds: number }
export const TIME_RANGES: TimeRange[] = [
  { label: '1m', seconds: 60 },
  { label: '5m', seconds: 300 },
  { label: '15m', seconds: 900 },
  { label: '1h', seconds: 3600 },
];

/** Points within the last `seconds` relative to `now` (unix seconds). */
export function filterRange(points: Point[], seconds: number, now: number): Point[] {
  const cutoff = now - seconds;
  return points.filter(([ts]) => ts >= cutoff);
}

export function nodeList(state: MetricsState): NodeSnapshot[] {
  return Object.values(state.nodes).sort((a, b) => (a.node_id === 'host' ? -1 : b.node_id === 'host' ? 1 : a.node_id.localeCompare(b.node_id)));
}

export function fleetAverage(nodes: NodeSnapshot[], metric: Metric): number {
  const live = nodes.filter((n) => n.status !== 'down');
  if (live.length === 0) return 0;
  return live.reduce((sum, n) => sum + (n.metrics[metric] ?? 0), 0) / live.length;
}

export function firingCount(alerts: AlertStatus[]): number {
  return alerts.filter((a) => a.state === 'firing').length;
}
