const DEFAULT_RESEARCH_SETUP = {
  name: '',
  research_question: '',
  research_field: '',
  year_from: 2018,
  year_to: 2026,
  criteria_include: [],
  criteria_exclude: [],
};

export function normalizeResearchSetup(value) {
  const data = value && typeof value === 'object' ? value : {};
  return {
    ...DEFAULT_RESEARCH_SETUP,
    ...data,
    criteria_include: Array.isArray(data.criteria_include) ? data.criteria_include : [],
    criteria_exclude: Array.isArray(data.criteria_exclude) ? data.criteria_exclude : [],
  };
}
