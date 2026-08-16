export function shouldShowSectionTldr() {
  return false;
}

export function sectionEvidenceLabel(coverage) {
  const evidence = coverage?.evidence_count || 0;
  const papers = coverage?.paper_count || 0;
  return `${evidence} bằng chứng · ${papers} nguồn`;
}

// The synthesis panel already owns the page scroll. A nested 38vh scroller
// clips the report and makes the result look like a small embedded frame.
export const reviewScrollClass = 'overscroll-contain';
