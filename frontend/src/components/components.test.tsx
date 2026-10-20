import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { TIME_RANGES } from '@/lib/metrics';
import type { AlertRule, AlertStatus, NodeSnapshot, Notification } from '@/lib/types';
import { AlertsPanel } from './AlertsPanel';
import { ConnectionBadge } from './ConnectionBadge';
import { NodeGrid } from './NodeGrid';
import { TimeRangeSelector } from './TimeRangeSelector';

const node = (id: string, status: NodeSnapshot['status']): NodeSnapshot => ({
  node_id: id, name: `${id}-name`, region: 'dhaka-1', role: 'api', status, ts: 1,
  metrics: { cpu: 55.5, memory: 60, disk: 70, net_rx: 1500, net_tx: 200 },
});

describe('NodeGrid', () => {
  it('renders a card per node with status and selection', () => {
    const onSelect = vi.fn();
    render(<NodeGrid nodes={[node('host', 'healthy'), node('node-01', 'down')]} selected="host" onSelect={onSelect} />);
    expect(screen.getAllByRole('button')).toHaveLength(2);
    expect(screen.getByLabelText('down')).toBeInTheDocument();
    expect(screen.getByRole('button', { pressed: true })).toHaveTextContent('host-name');
    expect(screen.getAllByText('55.5%')).toHaveLength(2);
    fireEvent.click(screen.getByText('node-01-name'));
    expect(onSelect).toHaveBeenCalledWith('node-01');
  });
  it('shows a waiting message when empty', () => {
    render(<NodeGrid nodes={[]} selected={null} onSelect={() => {}} />);
    expect(screen.getByText(/waiting for the first collection tick/i)).toBeInTheDocument();
  });
});

describe('TimeRangeSelector', () => {
  it('marks the active range and emits changes', () => {
    const onChange = vi.fn();
    render(<TimeRangeSelector value={TIME_RANGES[1]} onChange={onChange} />);
    expect(screen.getByRole('radio', { name: '5m' })).toHaveAttribute('aria-checked', 'true');
    fireEvent.click(screen.getByRole('radio', { name: '1h' }));
    expect(onChange).toHaveBeenCalledWith(TIME_RANGES[3]);
  });
});

describe('ConnectionBadge', () => {
  it('reflects socket status and attempts', () => {
    const { rerender } = render(<ConnectionBadge info={{ status: 'open', attempts: 0, lastMessageAt: null }} />);
    expect(screen.getByTestId('connection-badge')).toHaveTextContent('Live');
    rerender(<ConnectionBadge info={{ status: 'reconnecting', attempts: 3, lastMessageAt: null }} />);
    expect(screen.getByTestId('connection-badge')).toHaveTextContent('Reconnecting· attempt 3');
  });
});

describe('AlertsPanel', () => {
  const rule: AlertRule = { id: 1, name: 'High CPU', metric: 'cpu', op: '>', threshold: 85, for_seconds: 10, severity: 'warning', node_filter: null, enabled: true };
  const alert: AlertStatus = { rule_id: 1, node_id: 'node-02', state: 'firing', breach_since: 90, fired_at: 100, resolved_at: null, last_value: 93.2 };
  const note: Notification = { id: 5, ts: 100, rule_id: 1, rule_name: 'High CPU', node_id: 'node-02', state: 'firing', severity: 'warning', value: 93.2, message: '[WARNING] High CPU FIRING on node-02: cpu=93.2 > 85' };

  it('lists firing alerts, rules and notifications', () => {
    const onToggle = vi.fn();
    render(<AlertsPanel alerts={[alert]} rules={[rule]} notifications={[note]} now={160} onToggleRule={onToggle} />);
    expect(screen.getByTestId('active-alerts')).toHaveTextContent('1 firing');
    expect(screen.getByTestId('active-alerts')).toHaveTextContent('for 1m 0s');
    expect(screen.getByTestId('notifications')).toHaveTextContent('High CPU FIRING on node-02');
    expect(screen.getByTestId('notifications')).toHaveTextContent('1m ago');
    fireEvent.click(screen.getByRole('switch', { name: 'toggle High CPU' }));
    expect(onToggle).toHaveBeenCalledWith(rule);
  });
  it('shows the quiet state', () => {
    render(<AlertsPanel alerts={[]} rules={[]} notifications={[]} now={0} />);
    expect(screen.getByText('All quiet.')).toBeInTheDocument();
    expect(screen.getByText('No alert transitions yet.')).toBeInTheDocument();
  });
});
