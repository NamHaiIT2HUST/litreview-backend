import test from 'node:test';
import assert from 'node:assert/strict';

import { persistedDirectUploadSources } from './workspaceSources.js';

test('persistedDirectUploadSources restores ingested direct uploads returned by backend', () => {
  const result = persistedDirectUploadSources([
    { id: 'p1', title: 'Uploaded paper', source: 'direct_upload', active_ingestion_id: 'i1' },
    { id: 'p2', title: 'Search result', source: 'scholar', active_ingestion_id: null },
  ]);

  assert.deepEqual(result, [{
    id: 'p1',
    title: 'Uploaded paper',
    filename: 'Uploaded paper.pdf',
    source: 'direct_upload',
    screening_decision: 'keep',
  }]);
});
