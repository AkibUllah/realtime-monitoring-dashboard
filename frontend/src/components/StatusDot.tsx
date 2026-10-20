import type { NodeStatus } from '@/lib/types';

export const STATUS_COLOR: Record<NodeStatus, string> = {
  healthy: 'bg-emerald-400',
  degraded: 'bg-amber-400',
  down: 'bg-rose-500',
};

export function StatusDot({ status }: { status: NodeStatus }) {
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${STATUS_COLOR[status]}`} aria-label={status} />;
}
