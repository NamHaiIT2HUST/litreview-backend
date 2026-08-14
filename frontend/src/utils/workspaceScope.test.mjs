import test from 'node:test';
import assert from 'node:assert/strict';
import { reconcileSelectedPaperIds, selectedPapersFromIds } from './workspaceScope.js';

test('reconciles selection without losing user choices and selects new sources', () => {
  const sources = [{ id: 'a' }, { id: 'b' }, { id: 'c' }];
  assert.deepEqual(reconcileSelectedPaperIds(['b'], sources), ['b', 'a', 'c']);
});

test('filters sources by the shared selected ids', () => {
  const sources = [{ id: 'a' }, { id: 'b' }];
  assert.deepEqual(selectedPapersFromIds(sources, ['b']), [{ id: 'b' }]);
});
