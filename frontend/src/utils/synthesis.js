export const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export function buildSynthesisRequest(workspacePapers, projectId = DEFAULT_PROJECT_ID, researchQuestion = null) {
  return {
    project_id: projectId,
    paper_ids: workspacePapers.map((paper) => paper.id),
    research_question: (researchQuestion && researchQuestion.trim()) ? researchQuestion.trim() : undefined,
  };
}

export function enrichCitation(citation, workspacePapers) {
  const paper = workspacePapers.find((item) => String(item.id) === String(citation.paper_id)) || {};
  return {
    ...citation,
    title: citation.title || paper.title || `Paper ${citation.paper_id}`,
    authors: paper.authors || '',
    journal: paper.journal || paper.venue || '',
    year: paper.year || null,
    filename: citation.filename || paper.filename || paper.uploadFilename || null,
    doi: paper.doi || '',
    url: paper.url || '#',
  };
}

export function buildReviewSections(result, workspacePapers) {
  const citationById = new Map(
    (result?.citations || []).map((citation) => [
      citation.id,
      enrichCitation(citation, workspacePapers),
    ]),
  );

  return (result?.sections || []).map((section) => ({
    ...section,
    sentences: (section.sentences || []).map((sentence) => ({
      ...sentence,
      citations: (sentence.citation_ids || [])
        .map((id) => citationById.get(id))
        .filter(Boolean),
    })),
  }));
}

/**
 * Builds comparison matrix rows with interactive evidence grounding for every cell.
 */
export function buildComparisonRows(evidenceProfile, workspacePapers, citations = []) {
  const citationByPaperId = new Map();
  (citations || []).forEach((cite) => {
    if (cite.paper_id && !citationByPaperId.has(cite.paper_id)) {
      citationByPaperId.set(cite.paper_id, cite);
    }
  });

  const buckets = new Map(
    workspacePapers.map((paper) => [paper.id, {
      paperId: paper.id,
      title: paper.title || `Paper ${paper.id}`,
      authors: paper.authors || '',
      year: paper.year || '',
      journal: paper.journal || paper.venue || '',
      filename: paper.filename || paper.uploadFilename || '',
      cells: {
        method: { value: '', quote: '', citation: null },
        dataset: { value: '', quote: '', citation: null },
        findings: { value: '', quote: '', citation: null },
        limitations: { value: '', quote: '', citation: null },
      },
      method: '',
      dataset: '',
      findings: '',
      limitations: '',
    }]),
  );

  for (const item of evidenceProfile || []) {
    const row = buckets.get(item.paper_id);
    if (!row) continue;
    const dimension = (item.dimension || '').toLowerCase();
    let field = null;
    if (dimension.includes('method') || dimension.includes('approach') || dimension.includes('algorithm')) field = 'method';
    else if (dimension.includes('dataset') || dimension.includes('population') || dimension.includes('benchmark')) field = 'dataset';
    else if (dimension.includes('finding') || dimension.includes('outcome') || dimension.includes('result')) field = 'findings';
    else if (dimension.includes('limitation') || dimension.includes('gap') || dimension.includes('constraint')) field = 'limitations';
    
    if (field && !row.cells[field].value) {
      const cite = citationByPaperId.get(item.paper_id);
      row.cells[field] = {
        value: item.value,
        quote: item.quote || item.value,
        citation: cite ? enrichCitation(cite, workspacePapers) : {
          paper_id: item.paper_id,
          title: row.title,
          filename: row.filename,
          quoted_snippet: item.quote || item.value,
        }
      };
      row[field] = item.value;
    }
  }

  return Array.from(buckets.values());
}

/**
 * Standardizes BibTeX generation with academic key conventions {firstAuthorSurname}{year}
 */
export function generateFullBibTeX(citations, workspacePapers) {
  if (!citations || citations.length === 0) return '';
  const seenKeys = new Map();
  const uniquePaperIds = new Set();
  const uniqueCitations = [];

  for (const cite of citations) {
    const pId = String(cite.paper_id || cite.id);
    if (!uniquePaperIds.has(pId)) {
      uniquePaperIds.add(pId);
      uniqueCitations.push(cite);
    }
  }

  return uniqueCitations.map((cite, index) => {
    const paper = workspacePapers.find((p) => String(p.id) === String(cite.paper_id)) || {};
    const authorStr = paper.authors || cite.authors || 'Unknown';
    let baseKey = authorStr.split(',')[0].trim().split(' ').pop().toLowerCase().replace(/[^a-z0-9]/g, '') || `paper${index + 1}`;
    const year = paper.year || cite.year || new Date().getFullYear();
    let citeKey = `${baseKey}${year}`;
    
    if (seenKeys.has(citeKey)) {
      const count = seenKeys.get(citeKey) + 1;
      seenKeys.set(citeKey, count);
      citeKey = `${citeKey}${String.fromCharCode(96 + count)}`;
    } else {
      seenKeys.set(citeKey, 1);
    }

    const title = cite.title || paper.title || 'Untitled Academic Paper';
    const journal = paper.journal || paper.venue || '';
    const doi = paper.doi || '';
    const url = paper.url && paper.url !== '#' ? paper.url : '';

    let entry = `@article{${citeKey},\n`;
    entry += `  title = {${title}},\n`;
    entry += `  author = {${authorStr}},\n`;
    if (journal) entry += `  journal = {${journal}},\n`;
    entry += `  year = {${year}}`;
    if (doi) entry += `,\n  doi = {${doi}}`;
    if (url) entry += `,\n  url = {${url}}`;
    entry += `\n}`;
    return entry;
  }).join('\n\n');
}

/**
 * Generates formatted APA 7th Edition reference entries.
 */
export function generateAPAReferences(citations, workspacePapers) {
  if (!citations || citations.length === 0) return [];
  const seenIds = new Set();
  const entries = [];

  for (const cite of citations) {
    const pId = String(cite.paper_id || cite.id);
    if (seenIds.has(pId)) continue;
    seenIds.add(pId);

    const paper = workspacePapers.find((p) => String(p.id) === String(cite.paper_id)) || {};
    const authorStr = paper.authors || cite.authors || 'Unknown Author';
    const year = paper.year || cite.year || 'n.d.';
    const title = cite.title || paper.title || 'Untitled Paper';
    const journal = paper.journal || paper.venue || '';
    const doi = paper.doi ? ` https://doi.org/${paper.doi}` : '';

    let text = `${authorStr} (${year}). ${title}.`;
    if (journal) text += ` *${journal}*.`;
    if (doi) text += `${doi}`;
    entries.push(text);
  }

  return entries;
}

/**
 * Generates formatted IEEE numbered reference entries.
 */
export function generateIEEEReferences(citations, workspacePapers) {
  if (!citations || citations.length === 0) return [];
  const seenIds = new Set();
  const entries = [];
  let count = 1;

  for (const cite of citations) {
    const pId = String(cite.paper_id || cite.id);
    if (seenIds.has(pId)) continue;
    seenIds.add(pId);

    const paper = workspacePapers.find((p) => String(p.id) === String(cite.paper_id)) || {};
    const authorStr = paper.authors || cite.authors || 'Unknown Author';
    const year = paper.year || cite.year || 'n.d.';
    const title = cite.title || paper.title || 'Untitled Paper';
    const journal = paper.journal || paper.venue || '';

    let text = `[${count}] ${authorStr}, "${title},"`;
    if (journal) text += ` *${journal}*,`;
    text += ` ${year}.`;
    entries.push(text);
    count++;
  }

  return entries;
}

/**
 * Generates CSV content with UTF-8 BOM for full Excel compatibility.
 */
export function generateCSVContent(comparisonRows = []) {
  const headers = ['Paper Title', 'Authors', 'Year', 'Proposed Methodology', 'Dataset / Benchmark', 'Core Findings', 'Limitations / Trade-offs'];
  
  const escapeCSV = (str) => {
    if (!str) return '""';
    const clean = String(str).replace(/"/g, '""').replace(/\r?\n/g, ' ');
    return `"${clean}"`;
  };

  const rows = comparisonRows.map((row) => [
    escapeCSV(row.title),
    escapeCSV(row.authors),
    escapeCSV(row.year),
    escapeCSV(row.cells?.method?.value || row.method || ''),
    escapeCSV(row.cells?.dataset?.value || row.dataset || ''),
    escapeCSV(row.cells?.findings?.value || row.findings || ''),
    escapeCSV(row.cells?.limitations?.value || row.limitations || ''),
  ].join(','));

  // Prepend UTF-8 BOM (\uFEFF) so Excel displays Vietnamese characters properly
  return '\uFEFF' + [headers.map(h => `"${h}"`).join(','), ...rows].join('\r\n');
}

/**
 * Generates an academic Markdown report with structured frontmatter, TOC,
 * narrative sections with citations, comparative matrix, and APA/IEEE references.
 */
export function generateAcademicMarkdown(result, workspacePapers, researchTopic = '', comparisonRows = []) {
  const title = researchTopic && researchTopic.trim() 
    ? `Literature Review: ${researchTopic.trim()}` 
    : 'Systematic Literature Review & Synthesis Report';
  
  const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  const paperCount = workspacePapers.length;

  let md = `# ${title}\n\n`;
  md += `**Date:** ${dateStr} | **Synthesized Papers:** ${paperCount}\n\n`;
  md += `---\n\n`;

  // Abstract / Executive Summary
  const { consensus, debates, gaps } = extractNoveltyAndGaps(result?.sections || [], comparisonRows);
  md += `## 1. Executive Summary & Key Takeaways\n\n`;
  if (consensus.length > 0) {
    md += `### Core Scientific Consensus\n`;
    consensus.forEach((c) => {
      md += `- ${c.text}\n`;
    });
    md += `\n`;
  }
  if (debates.length > 0) {
    md += `### Key Contradictions & Methodological Trade-offs\n`;
    debates.forEach((d) => {
      md += `- **[Debate]** ${d.text}\n`;
    });
    md += `\n`;
  }
  if (gaps.length > 0) {
    md += `### Unresolved Research Gaps & Open Opportunities\n`;
    gaps.forEach((g) => {
      md += `- **[Gap]** ${g.text}\n`;
    });
    md += `\n`;
  }

  // Comparative Matrix Table in Markdown
  if (comparisonRows.length > 0) {
    md += `## 2. Comparative Evidence Matrix\n\n`;
    md += `| Paper & Authors | Proposed Methodology | Dataset / Benchmark | Core Findings | Limitations / Trade-offs |\n`;
    md += `| :--- | :--- | :--- | :--- | :--- |\n`;
    comparisonRows.forEach((r) => {
      const pTitle = `${r.title} (${r.authors || 'Unknown'}, ${r.year || ''})`.replace(/\|/g, '-');
      const method = (r.cells?.method?.value || r.method || '—').replace(/\|/g, '-').replace(/\n/g, ' ');
      const dataset = (r.cells?.dataset?.value || r.dataset || '—').replace(/\|/g, '-').replace(/\n/g, ' ');
      const findings = (r.cells?.findings?.value || r.findings || '—').replace(/\|/g, '-').replace(/\n/g, ' ');
      const limits = (r.cells?.limitations?.value || r.limitations || '—').replace(/\|/g, '-').replace(/\n/g, ' ');
      md += `| **${pTitle}** | ${method} | ${dataset} | ${findings} | ${limits} |\n`;
    });
    md += `\n`;
  }

  // Narrative Synthesis Sections
  md += `## 3. Thematic Literature Review\n\n`;
  if (result?.sections && result.sections.length > 0) {
    result.sections.forEach((sec, idx) => {
      md += `### 3.${idx + 1}. ${sec.title}\n\n`;
      const sectionText = (sec.sentences || []).map(s => {
        const cites = (s.citations || []).map(c => `[${c.marker_display || '#'}]`).join('');
        return `${s.text} ${cites}`.trim();
      }).join(' ');
      md += `${sectionText}\n\n`;
    });
  } else if (result?.review_markdown) {
    md += `${result.review_markdown}\n\n`;
  }

  // References Section (APA 7th & IEEE)
  md += `## 4. References & Bibliography\n\n`;
  const apaRefs = generateAPAReferences(result?.citations || [], workspacePapers);
  if (apaRefs.length > 0) {
    md += `### References (APA 7th Edition)\n\n`;
    apaRefs.forEach((ref) => {
      md += `- ${ref}\n`;
    });
    md += `\n`;
  }

  const ieeeRefs = generateIEEEReferences(result?.citations || [], workspacePapers);
  if (ieeeRefs.length > 0) {
    md += `### References (IEEE Format)\n\n`;
    ieeeRefs.forEach((ref) => {
      md += `${ref}\n\n`;
    });
  }

  return md;
}

/**
 * Extracts key novelty takeaways, consensus points, and open research gaps from synthesis sections and matrix rows.
 */
export function extractNoveltyAndGaps(reviewSections = [], comparisonRows = []) {
  const consensus = [];
  const debates = [];
  const gaps = [];

  // 1. Scan from narrative sections
  for (const section of reviewSections) {
    const title = (section.title || '').toLowerCase();
    for (const sent of section.sentences || []) {
      const text = sent.text || '';
      if (text.length < 25) continue;
      const lower = text.toLowerCase();

      if (
        title.includes('khoảng trống') || 
        title.includes('hướng mở') || 
        title.includes('hạn chế') ||
        title.includes('gap') ||
        title.includes('limitation') ||
        lower.includes('khoảng trống') || 
        lower.includes('chưa được') || 
        lower.includes('cần nghiên cứu thêm') ||
        lower.includes('hạn chế chính') ||
        lower.includes('unresolved') ||
        lower.includes('future work')
      ) {
        if (gaps.length < 6) gaps.push({ text, sectionTitle: section.title, citations: sent.citations });
      } else if (
        lower.includes('tuy nhiên') || 
        lower.includes('trái lại') || 
        lower.includes('mâu thuẫn') || 
        lower.includes('khác biệt') || 
        lower.includes('bất đồng') ||
        lower.includes('trong khi đó') ||
        lower.includes('contrast') ||
        lower.includes('whereas') ||
        lower.includes('however')
      ) {
        if (debates.length < 5) debates.push({ text, sectionTitle: section.title, citations: sent.citations });
      } else if (sent.sentence_type === 'claim' && consensus.length < 5) {
        consensus.push({ text, sectionTitle: section.title, citations: sent.citations });
      }
    }
  }

  // 2. Scan limitations from comparison matrix rows if gaps are still sparse
  if (gaps.length < 3 && comparisonRows && comparisonRows.length > 0) {
    for (const row of comparisonRows) {
      const limitVal = row.cells?.limitations?.value || row.limitations;
      if (limitVal && limitVal.length > 20 && !gaps.some(g => g.text === limitVal)) {
        gaps.push({
          text: `${row.title}: ${limitVal}`,
          sectionTitle: 'Hạn chế được trích xuất từ tài liệu',
          citations: [row.cells?.limitations?.citation].filter(Boolean),
        });
        if (gaps.length >= 5) break;
      }
    }
  }

  return { consensus, debates, gaps };
}

/**
 * Generates smart follow-up research questions based on the review topic and papers.
 */
export function generateFollowUpQuestions(result, researchTopic = '') {
  const defaultQuestions = [
    "So sánh sâu hơn về độ phức tạp tính toán và hiệu năng thực nghiệm giữa các phương pháp tiếp cận.",
    "Những nguyên nhân cốt lõi nào dẫn đến sự khác biệt về kết quả giữa các nghiên cứu?",
    "Làm thế nào để kết hợp các ưu điểm của các mô hình hàng đầu nhằm giải quyết khoảng trống nghiên cứu hiện tại?",
    "Đề xuất khung thực nghiệm (Benchmark framework) chuẩn hóa để đánh giá công bằng các thuật toán."
  ];

  if (researchTopic && researchTopic.trim().length > 10) {
    return [
      `Phân tích các trường hợp ngoại lệ (Edge cases) đối với chủ đề "${researchTopic}".`,
      `So sánh chi tiết ưu nhược điểm định lượng của từng phương pháp liên quan đến "${researchTopic}".`,
      `Các hướng mở đột phá nào chưa được khai thác sâu liên quan đến "${researchTopic}"?`,
      "Đề xuất quy trình thực nghiệm tối ưu kết hợp các phát hiện trên."
    ];
  }

  return defaultQuestions;
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
