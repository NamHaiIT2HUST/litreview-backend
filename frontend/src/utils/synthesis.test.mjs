import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildReviewSections,
  buildSynthesisRequest,
  enrichCitation,
  tokenizeReviewCitations,
} from './synthesis.js';

test('buildReviewSections joins each sentence to its grounded citations', () => {
  const result = {
    citations: [{ id: 'citation-1', paper_id: 'paper-1', marker_display: '[1]' }],
    sections: [{
      id: 'section-1',
      title: 'Kết quả chính',
      coverage: { status: 'sufficient', evidence_count: 2, paper_count: 2, retrieval_attempts: 1, reasons: [] },
      sentences: [
        { text: 'RAG cải thiện độ chính xác.', sentence_type: 'claim', claim_ids: ['claim-1'], citation_ids: ['citation-1'] },
        { text: 'Nhìn chung, các kết quả nhất quán.', sentence_type: 'discourse', claim_ids: ['claim-1'], citation_ids: [] },
      ],
    }],
  };

  const [section] = buildReviewSections(result, [{ id: 'paper-1', title: 'Paper A' }]);

  assert.equal(section.sentences[0].citations[0].title, 'Paper A');
  assert.equal(section.sentences[1].citations.length, 0);
  assert.equal(section.sentences[1].sentence_type, 'discourse');
});

test('buildSynthesisRequest uses canonical workspace paper ids in order', () => {
  const request = buildSynthesisRequest([
    { id: '11111111-1111-1111-1111-111111111111' },
    { id: '22222222-2222-2222-2222-222222222222' },
  ], '00000000-0000-0000-0000-000000000001');

  assert.deepEqual(request.paper_ids, [
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
  ]);
});

test('enrichCitation attaches workspace paper metadata to grounded source', () => {
  const citation = {
    paper_id: '11111111-1111-1111-1111-111111111111',
    marker_display: '[1]',
    quoted_snippet: 'No significant difference was observed.',
  };
  const enriched = enrichCitation(citation, [
    { id: citation.paper_id, title: 'Paper A', authors: 'Alice' },
  ]);

  assert.equal(enriched.title, 'Paper A');
  assert.equal(enriched.quoted_snippet, citation.quoted_snippet);
});

test('tokenizeReviewCitations resolves duplicate markers by exact review offset', () => {
  const review = 'Finding A[1]. Finding B[1].';
  const citations = [
    { id: 'c1', marker_display: '[1]', review_char_start: 9 },
    { id: 'c2', marker_display: '[1]', review_char_start: 23 },
  ];

  const tokens = tokenizeReviewCitations(review, citations);
  const citationTokens = tokens.filter(token => token.type === 'citation');

  assert.equal(citationTokens[0].citation.id, 'c1');
  assert.equal(citationTokens[1].citation.id, 'c2');
});

test('tokenizeReviewCitations falls back to citation order when UTF-16 offsets differ', () => {
  const review = '𝛼 finding[1].';
  const markerIndexInPythonCodePoints = Array.from(review).indexOf('[');
  const citation = {
    id: 'c-unicode',
    marker_display: '[1]',
    review_char_start: markerIndexInPythonCodePoints,
  };

  const tokens = tokenizeReviewCitations(review, [citation]);
  const token = tokens.find((item) => item.type === 'citation');

  assert.equal(token?.citation.id, 'c-unicode');
});
