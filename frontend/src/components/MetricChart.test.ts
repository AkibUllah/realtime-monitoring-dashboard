import { describe, expect, it } from 'vitest';
import { mergeSeries } from './MetricChart';

describe('mergeSeries', () => {
  it('aligns series by timestamp and sorts rows', () => {
    const rows = mergeSeries([
      { key: 'a', label: 'a', metric: 'cpu', color: '#000', points: [[2, 20], [1, 10]] },
      { key: 'b', label: 'b', metric: 'cpu', color: '#000', points: [[2, 200], [3, 300]] },
    ]);
    expect(rows).toEqual([{ ts: 1, a: 10 }, { ts: 2, a: 20, b: 200 }, { ts: 3, b: 300 }]);
  });
});
