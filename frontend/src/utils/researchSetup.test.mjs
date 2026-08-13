import test from 'node:test';
import assert from 'node:assert/strict';

import { normalizeResearchSetup } from './researchSetup.js';

test('normalizeResearchSetup converts nullable criteria from cached or API data to arrays', () => {
  const result = normalizeResearchSetup({
    research_question: 'Question',
    criteria_include: null,
    criteria_exclude: null,
  });

  assert.deepEqual(result.criteria_include, []);
  assert.deepEqual(result.criteria_exclude, []);
  assert.equal(result.research_question, 'Question');
});
