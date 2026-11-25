import { describe, expect, it } from 'vitest';
import { filterRange, firingCount, fleetAverage, initialMetricsState, metricsReducer, nodeList } from './metrics';
import type { NodeSnapshot, SnapshotMessage, TickMessage } from './types';

const node = (id: string, ts: number, cpu: number, status: NodeSnapshot['status'] = 'healthy'): NodeSnapshot => ({
  node_id: id, name: id, region: 'dhaka-1', role: 'api', status, ts,
  metrics: { cpu, memory: 50, disk: 40, net_rx: 100, net_tx: 80 },
});

const snapshot: SnapshotMessage = {
  type: 'snapshot', ts: 1000,
  nodes: [node('node-01', 1000, 30), node('host', 1000, 10)],
  history: { 'node-01': { cpu: [[996, 20], [998, 25]] } },
  alerts: [], rules: [], notifications: [{ id: 1, ts: 999, rule_id: 1, rule_name: 'r', node_id: 'node-01', state: 'firing', severity: 'warning', value: 1, message: 'm' }],
};

describe('metricsReducer', () => {
  it('keeps bucket averages and appends only live points after a sampled snapshot', () => {
    const sampled: SnapshotMessage = {
      ...snapshot, step: 13, ts: 1010,
      history: { 'node-01': { cpu: [[988, 20], [1001, 40]] } },
      nodes: [node('node-01', 1008, 90)],
    };
    let s = metricsReducer(initialMetricsState(), { type: 'message', message: sampled });
    expect(s.series['node-01'].cpu).toEqual([[988, 20], [1001, 40]]);
    expect(s.nodes['node-01'].metrics.cpu).toBe(90);
    const tick: TickMessage = { type: 'tick', ts: 1012, nodes: [node('node-01', 1012, 60)], alerts: [], notifications: [] };
    s = metricsReducer(s, { type: 'message', message: { ...tick, ts: 1008, nodes: [node('node-01', 1008, 90)] } });
    expect(s.series['node-01'].cpu).toEqual([[988, 20], [1001, 40]]);
    s = metricsReducer(s, { type: 'message', message: tick });
    s = metricsReducer(s, { type: 'message', message: tick });
    expect(s.series['node-01'].cpu).toEqual([[988, 20], [1001, 40], [1012, 60]]);
    s = metricsReducer(s, { type: 'message', message: { ...sampled, ts: 1023, history: { 'node-01': { cpu: [[1001, 50], [1014, 70]] } }, nodes: [node('node-01', 1022, 80)] } });
    expect(s.series['node-01'].cpu).toEqual([[1001, 50], [1014, 70]]);
  });
  it('loads history and appends the snapshot tick', () => {
    const s = metricsReducer(initialMetricsState(), { type: 'message', message: snapshot });
    expect(s.series['node-01'].cpu).toEqual([[996, 20], [998, 25], [1000, 30]]);
    expect(s.series['host'].cpu).toEqual([[1000, 10]]);
    expect(s.lastTs).toBe(1000);
  });
  it('appends ticks and ignores out-of-order replays', () => {
    let s = metricsReducer(initialMetricsState(), { type: 'message', message: snapshot });
    const tick: TickMessage = { type: 'tick', ts: 1002, nodes: [node('node-01', 1002, 35)], alerts: [], notifications: [] };
    s = metricsReducer(s, { type: 'message', message: tick });
    s = metricsReducer(s, { type: 'message', message: { ...tick, ts: 1001, nodes: [node('node-01', 1001, 99)] } });
    expect(s.series['node-01'].cpu?.map((p) => p[1])).toEqual([20, 25, 30, 35]);
    expect(s.nodes['node-01'].metrics.cpu).toBe(99); // latest snapshot still updates the card
  });
  it('trims samples older than the retention window', () => {
    let s = metricsReducer(initialMetricsState(10), { type: 'message', message: snapshot });
    s = metricsReducer(s, { type: 'message', message: { type: 'tick', ts: 1009, nodes: [node('node-01', 1009, 1)], alerts: [], notifications: [] } });
    expect(s.series['node-01'].cpu?.map((p) => p[0])).toEqual([1000, 1009]);
  });
  it('merges notifications newest-first without duplicates', () => {
    let s = metricsReducer(initialMetricsState(), { type: 'message', message: snapshot });
    const n = snapshot.notifications[0];
    s = metricsReducer(s, { type: 'message', message: { type: 'tick', ts: 1002, nodes: [], alerts: [], notifications: [n, { ...n, id: 2, ts: 1002 }] } });
    expect(s.notifications.map((x) => x.id)).toEqual([2, 1]);
  });
  it('a reconnect snapshot replaces history', () => {
    let s = metricsReducer(initialMetricsState(), { type: 'message', message: snapshot });
    s = metricsReducer(s, { type: 'message', message: { ...snapshot, ts: 2000, history: { 'node-01': { cpu: [[1998, 5]] } }, nodes: [node('node-01', 2000, 6)] } });
    expect(s.series['node-01'].cpu).toEqual([[1998, 5], [2000, 6]]);
  });
  it('ignores pong frames', () => {
    const s = initialMetricsState();
    expect(metricsReducer(s, { type: 'message', message: { type: 'pong', ts: 1 } })).toBe(s);
  });
});

describe('helpers', () => {
  it('filterRange keeps only the trailing window', () => {
    expect(filterRange([[1, 1], [50, 2], [100, 3]], 60, 100)).toEqual([[50, 2], [100, 3]]);
  });
  it('nodeList puts host first then sorts by id', () => {
    const s = metricsReducer(initialMetricsState(), { type: 'message', message: snapshot });
    expect(nodeList(s).map((n) => n.node_id)).toEqual(['host', 'node-01']);
  });
  it('fleetAverage skips down nodes', () => {
    expect(fleetAverage([node('a', 1, 10), node('b', 1, 30), node('c', 1, 0, 'down')], 'cpu')).toBe(20);
    expect(fleetAverage([], 'cpu')).toBe(0);
  });
  it('firingCount counts only firing states', () => {
    expect(firingCount([{ rule_id: 1, node_id: 'a', state: 'firing', breach_since: null, fired_at: null, resolved_at: null, last_value: null }, { rule_id: 1, node_id: 'b', state: 'resolved', breach_since: null, fired_at: null, resolved_at: null, last_value: null }])).toBe(1);
  });
});
