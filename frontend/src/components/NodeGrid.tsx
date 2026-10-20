import { formatValue } from '@/lib/format';
import type { NodeSnapshot } from '@/lib/types';
import { StatusDot } from './StatusDot';

interface Props { nodes: NodeSnapshot[]; selected: string | null; onSelect: (id: string) => void }

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded bg-ink-700">
      <div className={`h-full ${color}`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export function NodeGrid({ nodes, selected, onSelect }: Props) {
  if (nodes.length === 0) return <p className="text-sm text-slate-500">Waiting for the first collection tick…</p>;
  return (
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" data-testid="node-grid">
      {nodes.map((n) => {
        const active = n.node_id === selected;
        const down = n.status === 'down';
        return (
          <li key={n.node_id}>
            <button
              type="button"
              onClick={() => onSelect(n.node_id)}
              aria-pressed={active}
              className={`w-full rounded-xl border p-3 text-left transition ${
                active ? 'border-sky-500/60 bg-sky-500/10' : 'border-ink-700/70 bg-ink-900/70 hover:border-ink-600'
              } ${down ? 'opacity-70' : ''}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex items-center gap-2 truncate text-sm font-medium text-slate-100">
                  <StatusDot status={n.status} />
                  <span className="truncate">{n.name}</span>
                </span>
                <span className="chip bg-ink-800 text-slate-400">{n.role}</span>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{n.node_id} · {n.region}</p>
              <dl className="mt-3 space-y-2 text-xs">
                {(['cpu', 'memory', 'disk'] as const).map((m) => (
                  <div key={m}>
                    <div className="mb-0.5 flex justify-between text-slate-400">
                      <dt className="uppercase">{m}</dt>
                      <dd className="font-mono text-slate-200">{formatValue(m, n.metrics[m])}</dd>
                    </div>
                    <Bar value={n.metrics[m]} color={m === 'cpu' ? 'bg-accent-cpu' : m === 'memory' ? 'bg-accent-memory' : 'bg-accent-disk'} />
                  </div>
                ))}
                <div className="flex justify-between text-slate-400">
                  <dt>net</dt>
                  <dd className="font-mono text-slate-200">↓ {formatValue('net_rx', n.metrics.net_rx)} · ↑ {formatValue('net_tx', n.metrics.net_tx)}</dd>
                </div>
              </dl>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
