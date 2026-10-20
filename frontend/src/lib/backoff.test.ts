import { describe, expect, it } from 'vitest';
import { nextDelay } from './backoff';

describe('nextDelay', () => {
  it('grows exponentially and is capped', () => {
    const full = { random: () => 1 };
    expect([0, 1, 2, 3].map((a) => nextDelay(a, { base: 500, cap: 30_000, ...full }))).toEqual([500, 1000, 2000, 4000]);
    expect(nextDelay(20, { base: 500, cap: 30_000, ...full })).toBe(30_000);
  });
  it('applies full jitter within [0, exp]', () => {
    expect(nextDelay(3, { base: 500, random: () => 0.5 })).toBe(2000);
    expect(nextDelay(3, { base: 500, random: () => 0 })).toBe(0);
  });
});
