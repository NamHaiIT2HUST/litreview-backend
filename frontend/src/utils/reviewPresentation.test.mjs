import test from 'node:test';
import assert from 'node:assert/strict';

import { reviewScrollClass, sectionEvidenceLabel, shouldShowSectionTldr } from './reviewPresentation.js';

test('article view does not repeat generated section TLDR above the same prose', () => {
  assert.equal(shouldShowSectionTldr(), false);
});

test('coverage label reports grounded evidence and source counts', () => {
  assert.equal(
    sectionEvidenceLabel({ evidence_count: 4, paper_count: 2 }),
    '4 bằng chứng · 2 nguồn',
  );
});

test('review article scrolls internally so it cannot push chat out of view', () => {
  assert.match(reviewScrollClass, /max-h-/);
  assert.match(reviewScrollClass, /overflow-y-auto/);
});
