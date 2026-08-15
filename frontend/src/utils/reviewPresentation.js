export function shouldShowSectionTldr() {
  return false;
}

export function sectionEvidenceLabel(coverage) {
  const evidence = coverage?.evidence_count || 0;
  const papers = coverage?.paper_count || 0;
  return `${evidence} bằng chứng · ${papers} nguồn`;
}

export const reviewScrollClass = 'max-h-[38vh] overflow-y-auto overscroll-contain';
