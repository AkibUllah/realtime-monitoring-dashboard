import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatClock, formatValue } from '@/lib/format';
import type { Metric, Point } from '@/lib/types';

export interface Series { key: string; label: string; metric: Metric; color: string; points: Point[] }

interface Props { title: string; series: Series[]; unit: 'percent' | 'kbps'; height?: number }

/** Merge several [ts, value] series into Recharts rows keyed by timestamp. */
export function mergeSeries(series: Series[]): Record<string, number>[] {
  const rows = new Map<number, Record<string, number>>();
  for (const s of series) {
    for (const [ts, v] of s.points) {
      const row = rows.get(ts) ?? { ts };
      row[s.key] = v;
      rows.set(ts, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.ts - b.ts);
}

export function MetricChart({ title, series, unit, height = 220 }: Props) {
  const data = mergeSeries(series);
  const latest = series.map((s) => ({ s, last: s.points[s.points.length - 1]?.[1] }));
  return (
    <section className="panel">
      <header className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        <div className="flex gap-3 text-xs">
          {latest.map(({ s, last }) => (
            <span key={s.key} className="flex items-center gap-1 text-slate-400">
              <span className="h-2 w-2 rounded-sm" style={{ background: s.color }} />
              {s.label} <span className="font-mono text-slate-200">{last === undefined ? '—' : formatValue(s.metric, last)}</span>
            </span>
          ))}
        </div>
      </header>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
            <defs>
              {series.map((s) => (
                <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.color} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={s.color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid stroke="#273246" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="ts" type="number" domain={['dataMin', 'dataMax']} tickFormatter={formatClock} stroke="#3a4660" tick={{ fill: '#94a3b8', fontSize: 11 }} minTickGap={40} />
            <YAxis
              domain={unit === 'percent' ? [0, 100] : [0, 'auto']}
              tickFormatter={(v: number) => (unit === 'percent' ? `${v}` : `${Math.round(v / 1000)}M`)}
              stroke="#3a4660"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              width={56}
            />
            <Tooltip
              contentStyle={{ background: '#111827', border: '1px solid #273246', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#94a3b8' }}
              labelFormatter={(v) => formatClock(Number(v))}
              formatter={(value, name) => {
                const s = series.find((x) => x.key === name);
                return [s ? formatValue(s.metric, Number(value)) : String(value), s?.label ?? String(name)];
              }}
            />
            {series.map((s) => (
              <Area key={s.key} type="monotone" dataKey={s.key} stroke={s.color} fill={`url(#grad-${s.key})`} strokeWidth={1.8} dot={false} isAnimationActive={false} connectNulls />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
