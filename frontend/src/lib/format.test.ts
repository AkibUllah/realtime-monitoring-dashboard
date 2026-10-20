import { describe, expect, it } from 'vitest';
import { formatDuration, formatKbps, formatRelative, formatValue } from './format';

describe('format', () => {
  it('formats percentages and bandwidth', () => {
    expect(formatValue('cpu', 42.456)).toBe('42.5%');
    expect(formatValue('memory', 100)).toBe('100%');
    expect(formatKbps(512)).toBe('512 kbps');
    expect(formatValue('net_rx', 4200)).toBe('4.2 Mbps');
    expect(formatKbps(2_500_000)).toBe('2.50 Gbps');
  });
  it('formats relative time and durations', () => {
    expect(formatRelative(100, 102)).toBe('just now');
    expect(formatRelative(100, 130)).toBe('30s ago');
    expect(formatRelative(100, 400)).toBe('5m ago');
    expect(formatDuration(45)).toBe('45s');
    expect(formatDuration(125)).toBe('2m 5s');
    expect(formatDuration(3700)).toBe('1h 1m');
  });
});
