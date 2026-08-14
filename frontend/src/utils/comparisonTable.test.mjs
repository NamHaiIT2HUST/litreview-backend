import test from 'node:test';
import assert from 'node:assert/strict';

import { buildComparisonRows } from './synthesis.js';

test('builds one comparison row per selected paper from grounded evidence', () => {
  const papers = [
    { id: 'p1', title: 'Paper One' },
    { id: 'p2', title: 'Paper Two' },
  ];
  const evidence = [
    { paper_id: 'p1', dimension: 'Methodology and approach', value: 'Uses a CNN.' },
    { paper_id: 'p1', dimension: 'Main findings and outcomes', value: 'Improves accuracy.' },
    { paper_id: 'p2', dimension: 'Dataset and user population', value: 'Evaluated on MNIST.' },
  ];

  assert.deepEqual(buildComparisonRows(evidence, papers), [
    {
      paperId: 'p1', title: 'Paper One',
      method: 'Uses a CNN.', dataset: '', findings: 'Improves accuracy.', limitations: '',
    },
    {
      paperId: 'p2', title: 'Paper Two',
      method: '', dataset: 'Evaluated on MNIST.', findings: '', limitations: '',
    },
  ]);
});
