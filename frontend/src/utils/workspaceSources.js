export function persistedDirectUploadSources(papers) {
  return (papers || [])
    .filter((paper) => paper.source === 'direct_upload' && paper.active_ingestion_id)
    .map((paper) => ({
      id: paper.id,
      title: paper.title,
      filename: `${paper.title}.pdf`,
      source: 'direct_upload',
      screening_decision: 'keep',
    }));
}
