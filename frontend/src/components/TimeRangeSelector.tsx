import { TIME_RANGES, type TimeRange } from '@/lib/metrics';

export function TimeRangeSelector({ value, onChange }: { value: TimeRange; onChange: (r: TimeRange) => void }) {
  return (
    <div role="radiogroup" aria-label="Time range" className="inline-flex rounded-lg border border-ink-700 bg-ink-900 p-0.5">
      {TIME_RANGES.map((r) => (
        <button
          key={r.label}
          type="button"
          role="radio"
          aria-checked={r.seconds === value.seconds}
          onClick={() => onChange(r)}
          className={`btn-ghost ${r.seconds === value.seconds ? 'btn-ghost-active' : ''}`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}
