export const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export function buildSynthesisRequest(workspacePapers, projectId = DEFAULT_PROJECT_ID) {
  return {
    project_id: projectId,
    paper_ids: workspacePapers.map((paper) => paper.id),
  };
}

export function enrichCitation(citation, workspacePapers) {
  const paper = workspacePapers.find((item) => item.id === citation.paper_id) || {};
  return {
    ...citation,
    title: paper.title || `Paper ${citation.paper_id}`,
    authors: paper.authors || '',
    journal: paper.journal || '',
    year: paper.year || null,
    doi: paper.doi || '',
    url: paper.url || '#',
  };
}

export function tokenizeReviewCitations(review, citations) {
  const text = review || '';
  const tokens = [];
  const regex = /\[\d+\]/g;
  const orderedCitations = [...(citations || [])].sort(
    (a, b) => (a.review_char_start ?? Number.MAX_SAFE_INTEGER) - (b.review_char_start ?? Number.MAX_SAFE_INTEGER),
  );
  const usedCitationIds = new Set();
  let cursor = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > cursor) {
      tokens.push({ type: 'text', text: text.slice(cursor, match.index) });
    }

    // Prefer exact backend offsets. Python counts Unicode code points while JS
    // regex indices count UTF-16 code units, so a non-BMP character before a
    // marker can make those numeric offsets differ. Resolver-owned markers are
    // guaranteed by the backend, therefore ordered marker fallback is safe.
    let citation = orderedCitations.find(
      (item) => !usedCitationIds.has(item.id)
        && item.review_char_start === match.index
        && item.marker_display === match[0],
    );
    if (!citation) {
      citation = orderedCitations.find(
        (item) => !usedCitationIds.has(item.id) && item.marker_display === match[0],
      );
    }

    if (citation) {
      usedCitationIds.add(citation.id);
      tokens.push({ type: 'citation', text: match[0], citation });
    } else {
      tokens.push({ type: 'text', text: match[0] });
    }
    cursor = match.index + match[0].length;
  }

  if (cursor < text.length) {
    tokens.push({ type: 'text', text: text.slice(cursor) });
  }
  return tokens;
}
