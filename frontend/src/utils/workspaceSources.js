export function persistedDirectUploadSources(papers) {
  return (papers || [])
    .filter((paper) => paper.source === 'direct_upload')
    .map((paper) => ({
      id: String(paper.id),
      title: paper.title,
      filename: `${paper.title}.pdf`,
      totalPages: paper.total_pages,
      totalChunks: paper.total_chunks,
      source: 'direct_upload',
      screening_decision: 'keep',
    }));
}
