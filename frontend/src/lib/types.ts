export type Metric = 'cpu' | 'memory' | 'disk' | 'net_rx' | 'net_tx';
export const METRICS: Metric[] = ['cpu', 'memory', 'disk', 'net_rx', 'net_tx'];

export type NodeStatus = 'healthy' | 'degraded' | 'down';

export interface NodeSnapshot {
  node_id: string;
  name: string;
  region: string;
  role: string;
  status: NodeStatus;
  ts: number;
  metrics: Record<Metric, number>;
}

export type AlertState = 'ok' | 'firing' | 'resolved';
export type Severity = 'info' | 'warning' | 'critical';

export interface AlertStatus {
  rule_id: number;
  node_id: string;
  state: AlertState;
  breach_since: number | null;
  fired_at: number | null;
  resolved_at: number | null;
  last_value: number | null;
}

export interface AlertRule {
  id: number;
  name: string;
  metric: Metric;
  op: '>' | '>=' | '<' | '<=';
  threshold: number;
  for_seconds: number;
  severity: Severity;
  node_filter: string | null;
  enabled: boolean;
}

export interface Notification {
  id: number;
  ts: number;
  rule_id: number;
  rule_name: string;
  node_id: string;
  state: AlertState;
  severity: Severity;
  value: number;
  message: string;
}

/** [unix seconds, value] */
export type Point = [number, number];

export interface SnapshotMessage {
  type: 'snapshot';
  ts: number;
  nodes: NodeSnapshot[];
  history: Record<string, Partial<Record<Metric, Point[]>>>;
  alerts: AlertStatus[];
  rules: AlertRule[];
  notifications: Notification[];
}

export interface TickMessage {
  type: 'tick';
  ts: number;
  nodes: NodeSnapshot[];
  alerts: AlertStatus[];
  notifications: Notification[];
}

export interface PongMessage { type: 'pong'; ts: number }

export type ServerMessage = SnapshotMessage | TickMessage | PongMessage;
