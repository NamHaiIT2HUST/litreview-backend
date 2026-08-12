/**
 * Client-side Export Utilities for LitReview Agent (M6 - Export)
 */

// Escape BibTeX special characters
export const escapeBibTeX = (text) => {
  if (!text) return '';
  return String(text)
    .replace(/\\/g, '\\textbackslash{}')
    .replace(/&/g, '\\&')
    .replace(/%/g, '\\%')
    .replace(/\$/g, '\\$')
    .replace(/#/g, '\\#')
    .replace(/_/g, '\\_')
    .replace(/\{/g, '\\{')
    .replace(/\}/g, '\\}')
    .replace(/~/g, '\\textasciitilde{}')
    .replace(/\^/g, '\\textasciicircum{}');
};

// Generate BibTeX citation key
export const generateCitationKey = (authors, year, title, existingKeys = new Set()) => {
  let authorStr = '';
  if (Array.isArray(authors) && authors.length > 0) {
    authorStr = String(authors[0]);
  } else if (typeof authors === 'string') {
    authorStr = authors.split(',')[0].split(';')[0].split(' and ')[0].trim();
  }

  const authorParts = authorStr.match(/[A-Za-z]+/g);
  const authorKey = authorParts ? authorParts[authorParts.length - 1] : 'Author';
  const yearKey = year ? String(year) : 'ND';

  const titleWords = (title || '').match(/[A-Za-z0-9]+/g) || [];
  let titleKey = 'Paper';
  for (const word of titleWords) {
    if (word.length >= 4 && !['with', 'from', 'that', 'this', 'some', 'using', 'study', 'review'].includes(word.toLowerCase())) {
      titleKey = word.charAt(0).toUpperCase() + word.slice(1);
      break;
    }
  }

  let baseKey = `${authorKey}${yearKey}${titleKey}`;
  let key = baseKey;
  let counter = 1;
  while (existingKeys.has(key)) {
    key = `${baseKey}_${counter}`;
    counter++;
  }
  existingKeys.add(key);
  return key;
};

// Client-side BibTeX generator
export const generateClientBibTeX = (papers) => {
  if (!papers || papers.length === 0) return '% No papers selected for export.';
  const existingKeys = new Set();
  
  return papers.map(p => {
    const title = p.title || 'Untitled';
    const authorsArr = Array.isArray(p.authors) ? p.authors : (p.authors ? [p.authors] : []);
    const authorsStr = authorsArr.length > 0 ? authorsArr.join(' and ') : 'Unknown';
    const key = generateCitationKey(authorsArr, p.year, title, existingKeys);

    const fields = [
      `  title = {${escapeBibTeX(title)}}`,
      `  author = {${escapeBibTeX(authorsStr)}}`
    ];

    if (p.journal) fields.push(`  journal = {${escapeBibTeX(p.journal)}}`);
    if (p.year) fields.push(`  year = {${p.year}}`);
    if (p.doi) fields.push(`  doi = {${escapeBibTeX(p.doi)}}`);
    if (p.issn) fields.push(`  issn = {${escapeBibTeX(p.issn)}}`);
    if (p.url && p.url !== '#') fields.push(`  url = {${escapeBibTeX(p.url)}}`);
    if (p.abstract) {
      const cleanAbstract = p.abstract.replace(/\s+/g, ' ').trim();
      fields.push(`  abstract = {${escapeBibTeX(cleanAbstract)}}`);
    }

    return `@article{${key},\n${fields.join(',\n')}\n}`;
  }).join('\n\n');
};

// Client-side CSV generator
export const generateClientCSV = (papers, includeAbstract = true) => {
  if (!papers || papers.length === 0) return 'ID,Title,Authors,Year,Journal,DOI,ISSN,Scopus Status,Decision';

  const headers = ['ID', 'Title', 'Authors', 'Year', 'Journal', 'DOI', 'ISSN', 'Scopus Status', 'Decision'];
  if (includeAbstract) headers.push('Abstract');

  const escapeCSV = (val) => {
    if (val === null || val === undefined) return '""';
    const str = String(val).replace(/"/g, '""');
    return `"${str}"`;
  };

  const rows = papers.map(p => {
    const authorsStr = Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || '');
    const row = [
      escapeCSV(p.id || ''),
      escapeCSV(p.title || ''),
      escapeCSV(authorsStr),
      escapeCSV(p.year || ''),
      escapeCSV(p.journal || ''),
      escapeCSV(p.doi || ''),
      escapeCSV(p.issn || ''),
      escapeCSV(p.scopus_status || p.scopusStatus || 'undetermined'),
      escapeCSV(p.screening_decision || p.decision || 'keep')
    ];
    if (includeAbstract) {
      row.push(escapeCSV(p.abstract || ''));
    }
    return row.join(',');
  });

  return '\ufeff' + [headers.join(','), ...rows].join('\n');
};

// Client-side Markdown Report generator
export const generateClientMarkdown = (papers, projectInfo = {}, draftText = '') => {
  const projName = projectInfo.name || 'Literature Review Project';
  const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC';

  const lines = [
    `# ${projName}`,
    ``,
    `**Exported Date:** ${timestamp}  `,
    `**Research Field:** ${projectInfo.research_field || 'General'}  `,
    `**Research Question:** ${projectInfo.research_question || 'N/A'}  `,
    ``,
    `---`,
    ``,
    `## 1. Executive Summary & Review Setup`,
    ``,
    `- **Inclusion Criteria:** ${projectInfo.criteria_include || 'N/A'}`,
    `- **Exclusion Criteria:** ${projectInfo.criteria_exclude || 'N/A'}`,
    `- **Total Papers Exported:** ${papers.length}`,
    ``,
    `### Papers Included in Synthesis`,
    ``,
    `| # | Title | Authors | Year | Journal | Scopus Status |`,
    `|---|-------|---------|------|---------|---------------|`
  ];

  papers.forEach((p, idx) => {
    const title = (p.title || 'Untitled').replace(/\|/g, '\\|');
    const authorsArr = Array.isArray(p.authors) ? p.authors : (p.authors ? [p.authors] : []);
    let authorsStr = authorsArr.slice(0, 2).join(', ');
    if (authorsArr.length > 2) authorsStr += ' et al.';
    authorsStr = authorsStr.replace(/\|/g, '\\|');
    const year = p.year || 'N/A';
    const journal = (p.journal || 'N/A').replace(/\|/g, '\\|');
    const scopus = p.scopus_status || p.scopusStatus || 'undetermined';

    lines.push(`| ${idx + 1} | ${title} | ${authorsStr} | ${year} | ${journal} | \`${scopus}\` |`);
  });

  lines.push(
    ``,
    `---`,
    ``,
    `## 2. Synthesis & Literature Review Draft`,
    ``,
    draftText && draftText.trim() ? draftText.trim() : `_No custom synthesis draft text provided yet. Review paper metadata and extracted citations below._`,
    ``,
    `---`,
    ``,
    `## 3. Detailed References & Bibliography`,
    ``
  );

  papers.forEach((p, idx) => {
    const title = p.title || 'Untitled';
    const authorsArr = Array.isArray(p.authors) ? p.authors : (p.authors ? [p.authors] : []);
    const authorsStr = authorsArr.join(', ');
    const year = p.year || 'N/A';
    const journal = p.journal ? ` *${p.journal}*.` : '';
    const doi = p.doi ? ` DOI: [${p.doi}](https://doi.org/${p.doi})` : '';

    lines.push(`[${idx + 1}] **${title}** (${year}). ${authorsStr}.${journal}${doi}`);
    if (p.abstract) {
      lines.push(`> **Abstract:** ${p.abstract}`);
    }
    lines.push(``);
  });

  return lines.join('\n');
};

// Client-side JSON Package generator
export const generateClientJSON = (papers, projectInfo = {}, draftText = '') => {
  const payload = {
    app: 'T165 LitReview Agent',
    exported_at: new Date().toISOString(),
    project: {
      name: projectInfo.name || 'Literature Review Project',
      research_question: projectInfo.research_question || '',
      research_field: projectInfo.research_field || '',
      criteria_include: projectInfo.criteria_include || '',
      criteria_exclude: projectInfo.criteria_exclude || ''
    },
    papers_count: papers.length,
    papers: papers,
    synthesis_draft: draftText || ''
  };
  return JSON.stringify(payload, null, 2);
};

// Browser File Downloader
export const downloadFile = (content, filename, contentType = 'text/plain;charset=utf-8') => {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
