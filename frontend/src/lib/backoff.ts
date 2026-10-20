/**
 * Exponential backoff with full jitter: delay = random(0, min(cap, base * 2^attempt)).
 * `random` is injectable so the schedule is testable.
 */
export function nextDelay(attempt: number, { base = 500, cap = 30_000, random = Math.random }: { base?: number; cap?: number; random?: () => number } = {}): number {
  const exp = Math.min(cap, base * 2 ** Math.max(0, attempt));
  return Math.round(exp * Math.min(1, Math.max(0, random())));
}
