import { useCallback, useEffect, useMemo, useReducer, useState } from 'react';
import { AlertsPanel } from '@/components/AlertsPanel';
import { ConnectionBadge } from '@/components/ConnectionBadge';
import { MetricChart, type Series } from '@/components/MetricChart';
import { NodeGrid } from '@/components/NodeGrid';
import { TimeRangeSelector } from '@/components/TimeRangeSelector';
import { useMetricsSocket } from '@/hooks/useMetricsSocket';
import { api, wsUrl } from '@/lib/api';
import { formatValue } from '@/lib/format';
import { TIME_RANGES, filterRange, firingCount, fleetAverage, initialMetricsState, metricsReducer, nodeList, type TimeRange } from '@/lib/metrics';
import type { AlertRule, Metric } from '@/lib/types';

const COLORS = { cpu: '#38bdf8', memory: '#a78bfa', disk: '#fbbf24', rx: '#34d399', tx: '#fb7185', fleet: '#64748b' };

export default function App() {
  const [state, dispatch] = useReducer(metricsReducer, undefined, () => initialMetricsState(3600));
  const [range, setRange] = useState<TimeRange>(TIME_RANGES[1]);
  const [selected, setSelected] = useState<string | null>(null);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const socket = useMetricsSocket(useMemo(wsUrl, []), dispatch);

  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now() / 1000), 1000);
    return () => window.clearInterval(t);
  }, []);

  const nodes = nodeList(state);
  useEffect(() => {
    if (!selected && nodes.length) setSelected(nodes[0].node_id);
  }, [nodes, selected]);

  const node = selected ? state.nodes[selected] : undefined;
  const pts = useCallback(
    (metric: Metric) => {
      const series = selected ? state.series[selected] ?? {} : {};
      return filterRange(series[metric] ?? [], range.seconds, state.lastTs ?? now);
    },
    [selected, state.series, range.seconds, state.lastTs, now],
  );

  const fleetCpu: Series[] = useMemo(() => {
    const others = nodes.filter((n) => n.node_id !== selected);
    const tsSet = new Map<number, number[]>();
    for (const n of others) {
      for (const [ts, v] of filterRange(state.series[n.node_id]?.cpu ?? [], range.seconds, state.lastTs ?? now)) {
        const arr = tsSet.get(ts) ?? [];
        arr.push(v);
        tsSet.set(ts, arr);
      }
    }
    const avg = [...tsSet.entries()].map(([ts, vs]) => [ts, vs.reduce((a, b) => a + b, 0) / vs.length] as [number, number]);
    return [{ key: 'fleet', label: 'fleet avg', metric: 'cpu', color: COLORS.fleet, points: avg.sort((a, b) => a[0] - b[0]) }];
  }, [nodes, selected, state.series, range.seconds, state.lastTs, now]);

  const toggleRule = async (rule: AlertRule) => {
    try {
      await api.toggleRule(rule.id, !rule.enabled);
      dispatch({ type: 'rules', rules: await api.rules() });
    } catch {
      /* the next snapshot will resync rules */
    }
  };

  const firing = firingCount(state.alerts);
  const down = nodes.filter((n) => n.status === 'down').length;

  return (
    <div className="mx-auto max-w-[1600px] px-4 py-5">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#1a2233" /><polyline points="4,22 10,14 15,19 21,8 28,16" fill="none" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <div>
            <h1 className="text-lg font-semibold text-white">Fleet Monitor</h1>
            <p className="text-xs text-slate-500">{nodes.length} nodes · {down} down · {firing} alert{firing === 1 ? '' : 's'} firing</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <TimeRangeSelector value={range} onChange={setRange} />
          <ConnectionBadge info={socket} />
        </div>
      </header>

      <section className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {(['cpu', 'memory', 'disk', 'net_rx'] as const).map((m) => (
          <div key={m} className="panel py-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">fleet avg {m.replace('_', ' ')}</p>
            <p className="mt-1 font-mono text-2xl text-white">{formatValue(m, fleetAverage(nodes, m))}</p>
          </div>
        ))}
      </section>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <NodeGrid nodes={nodes} selected={selected} onSelect={setSelected} />
          {node && (
            <>
              <p className="text-sm text-slate-400">
                Showing <span className="font-medium text-slate-100">{node.name}</span> ({node.node_id}) · last {range.label}
              </p>
              <div className="grid gap-4 lg:grid-cols-2">
                <MetricChart title="CPU %" unit="percent" series={[{ key: 'cpu', label: node.node_id, metric: 'cpu', color: COLORS.cpu, points: pts('cpu') }, ...fleetCpu]} />
                <MetricChart title="Memory %" unit="percent" series={[{ key: 'memory', label: node.node_id, metric: 'memory', color: COLORS.memory, points: pts('memory') }]} />
                <MetricChart title="Disk %" unit="percent" series={[{ key: 'disk', label: node.node_id, metric: 'disk', color: COLORS.disk, points: pts('disk') }]} />
                <MetricChart title="Network" unit="kbps" series={[{ key: 'net_rx', label: 'in', metric: 'net_rx', color: COLORS.rx, points: pts('net_rx') }, { key: 'net_tx', label: 'out', metric: 'net_tx', color: COLORS.tx, points: pts('net_tx') }]} />
              </div>
            </>
          )}
        </div>
        <AlertsPanel alerts={state.alerts} rules={state.rules} notifications={state.notifications} now={now} onToggleRule={toggleRule} />
      </div>
    </div>
  );
}
