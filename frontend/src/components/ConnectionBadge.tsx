import type { SocketInfo } from '@/hooks/useMetricsSocket';

const styles: Record<SocketInfo['status'], { dot: string; label: string }> = {
  connecting: { dot: 'bg-amber-400 animate-pulse', label: 'Connecting' },
  open: { dot: 'bg-emerald-400', label: 'Live' },
  reconnecting: { dot: 'bg-amber-400 animate-pulse', label: 'Reconnecting' },
  closed: { dot: 'bg-slate-500', label: 'Offline' },
};

export function ConnectionBadge({ info }: { info: SocketInfo }) {
  const s = styles[info.status];
  return (
    <span className="chip bg-ink-800 text-slate-300" data-testid="connection-badge" title={`WebSocket ${info.status}`}>
      <span className={`h-2 w-2 rounded-full ${s.dot}`} aria-hidden="true" />
      {s.label}
      {info.status === 'reconnecting' && info.attempts > 0 && <span className="text-slate-500">· attempt {info.attempts}</span>}
    </span>
  );
}
