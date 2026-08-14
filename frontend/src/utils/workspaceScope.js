export function reconcileSelectedPaperIds(previousIds, sources, includeNew = true) {
  const sourceIds = new Set(sources.map((source) => source.id));
  const retained = previousIds.filter((id) => sourceIds.has(id));
  if (!includeNew) return retained;
  const retainedIds = new Set(retained);
  return [...retained, ...sources.filter((source) => !retainedIds.has(source.id)).map((source) => source.id)];
}

export function selectedPapersFromIds(sources, selectedIds) {
  const selected = new Set(selectedIds);
  return sources.filter((source) => selected.has(source.id));
}
