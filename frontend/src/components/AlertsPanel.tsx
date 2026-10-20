import { formatDuration, formatRelative } from '@/lib/format';
import type { AlertRule, AlertStatus, Notification } from '@/lib/types';

interface Props {
  alerts: AlertStatus[];
  rules: AlertRule[];
  notifications: Notification[];
  now: number;
  onToggleRule?: (rule: AlertRule) => void;
}

const sevStyle = { info: 'bg-sky-500/15 text-sky-300', warning: 'bg-amber-500/15 text-amber-300', critical: 'bg-rose-500/15 text-rose-300' } as const;

export function AlertsPanel({ alerts, rules, notifications, now, onToggleRule }: Props) {
  const byId = new Map(rules.map((r) => [r.id, r]));
  const firing = alerts.filter((a) => a.state === 'firing');
  const resolved = alerts.filter((a) => a.state === 'resolved');
  return (
    <div className="space-y-4">
      <section className="panel" data-testid="active-alerts">
        <h3 className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-200">
          Active alerts
          <span className={`chip ${firing.length ? 'bg-rose-500/15 text-rose-300' : 'bg-emerald-500/15 text-emerald-300'}`}>{firing.length} firing</span>
        </h3>
        {firing.length === 0 && resolved.length === 0 && <p className="text-sm text-slate-500">All quiet.</p>}
        <ul className="space-y-2">
          {[...firing, ...resolved].map((a) => {
            const rule = byId.get(a.rule_id);
            return (
              <li key={`${a.rule_id}-${a.node_id}`} className="flex items-center justify-between rounded-lg bg-ink-800/70 px-3 py-2 text-sm">
                <div>
                  <p className="font-medium text-slate-100">
                    {rule?.name ?? `rule #${a.rule_id}`} <span className="text-slate-500">on</span> {a.node_id}
                  </p>
                  <p className="text-xs text-slate-400">
                    {rule ? `${rule.metric} ${rule.op} ${rule.threshold}` : ''}
                    {a.last_value !== null && <span className="font-mono"> · now {a.last_value}</span>}
                    {a.state === 'firing' && a.fired_at !== null && <span> · for {formatDuration(now - a.fired_at)}</span>}
                  </p>
                </div>
                <span className={`chip ${a.state === 'firing' ? sevStyle[rule?.severity ?? 'warning'] : 'bg-emerald-500/15 text-emerald-300'}`}>{a.state}</span>
              </li>
            );
          })}
        </ul>
      </section>

      <section className="panel">
        <h3 className="mb-2 text-sm font-semibold text-slate-200">Rules</h3>
        <ul className="divide-y divide-ink-700/60 text-sm">
          {rules.map((r) => (
            <li key={r.id} className="flex items-center justify-between py-1.5">
              <span className={r.enabled ? 'text-slate-200' : 'text-slate-500 line-through'}>
                {r.name} <span className="font-mono text-xs text-slate-500">{r.metric} {r.op} {r.threshold}{r.for_seconds ? ` for ${r.for_seconds}s` : ''}</span>
              </span>
              <span className="flex items-center gap-2">
                <span className={`chip ${sevStyle[r.severity]}`}>{r.severity}</span>
                {onToggleRule && (
                  <button type="button" role="switch" aria-checked={r.enabled} aria-label={`toggle ${r.name}`} onClick={() => onToggleRule(r)} className={`h-5 w-9 rounded-full p-0.5 transition ${r.enabled ? 'bg-sky-500' : 'bg-ink-600'}`}>
                    <span className={`block h-4 w-4 rounded-full bg-white transition ${r.enabled ? 'translate-x-4' : ''}`} />
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel" data-testid="notifications">
        <h3 className="mb-2 text-sm font-semibold text-slate-200">Notifications</h3>
        {notifications.length === 0 && <p className="text-sm text-slate-500">No alert transitions yet.</p>}
        <ul className="max-h-72 space-y-1.5 overflow-y-auto text-xs">
          {notifications.map((n) => (
            <li key={n.id} className="flex items-start gap-2 rounded bg-ink-800/50 px-2 py-1.5">
              <span className={`chip shrink-0 ${n.state === 'firing' ? sevStyle[n.severity] : 'bg-emerald-500/15 text-emerald-300'}`}>{n.state}</span>
              <span className="flex-1 text-slate-300">{n.message}</span>
              <time className="shrink-0 text-slate-500">{formatRelative(n.ts, now)}</time>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
