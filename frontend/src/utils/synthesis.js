export const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export function getDirectSynthesisError(payload) {
  if (!payload || (payload.synthesis_mode !== 'fast_v2_experimental' && payload.synthesis_mode !== 'fast_v2_section_scoped')) return null;
  if (payload.outcome === 'no_evidence') {
    return payload.detail || 'Không tìm thấy evidence trong các tài liệu đã chọn. Hãy ingest hoặc tải lại PDF.';
  }
  if (payload.grounded !== true || !Array.isArray(payload.citations) || payload.citations.length === 0) {
    return payload.grounding_warning || 'Synthesis không tạo được review có evidence và citation hợp lệ.';
  }
  return null;
}

/**
 * Fast v2 returns a completed review directly, whereas Legacy returns an
 * asynchronous session id. Convert only the direct Fast v2 shape to the
 * workspace's existing review presentation contract.
 */
export function normalizeSynthesisResponse(payload) {
  if (
    !payload ||
    (payload.synthesis_mode !== 'fast_v2_experimental' && payload.synthesis_mode !== 'fast_v2_section_scoped') ||
    typeof payload.text !== 'string' ||
    getDirectSynthesisError(payload)
  ) {
    return null;
  }

  return {
    ...payload,
    review_markdown: payload.text,
    citations: (payload.citations || []).map((citation, index) => ({
      ...citation,
      id: `${citation.evidence_id || index}:${citation.review_char_start ?? index}`,
      title: citation.paper_title || citation.title || '',
      marker_display: citation.citation_marker || citation.marker_display || '',
      source_page_display: citation.source_page == null ? null : citation.source_page + 1,
    })),
    sections: [],
    evidence_profile: [],
  };
}

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

  const storedSections = (result?.sections || []).map((section) => ({
    ...section,
    sentences: (section.sentences || []).map((sentence) => ({
      ...sentence,
      citations: (sentence.citation_ids || [])
        .map((id) => citationById.get(id))
        .filter(Boolean),
    })),
  }));
  if (storedSections.length || !result?.review_markdown) return storedSections;

  // Fast synthesis persists narrative markdown, not Legacy SynthesisSection
  // rows. Convert headings/paragraphs into the same presentation contract.
  const markdown = result.review_markdown;
  
  // Match markdown headers: "## 1. Title" or "**Title**"
  let headingRegex = /(?:^|\n)##\s+([^\n]+)/g;
  let matches = [...markdown.matchAll(headingRegex)];
  
  if (!matches.length) {
    headingRegex = /\*\*([^*\n]+)\*\*/g;
    matches = [...markdown.matchAll(headingRegex)];
  }

  const blocks = matches.length ? matches.map((match, index) => ({
    title: match[1].trim(),
    start: match.index + match[0].length,
    end: index + 1 < matches.length ? matches[index + 1].index : markdown.length,
  })) : [{ title: 'Literature Review', start: 0, end: markdown.length }];

  return blocks.map((block, index) => {
    const untrimmedBody = markdown.slice(block.start, block.end);
    const leadingWhitespace = untrimmedBody.length - untrimmedBody.trimStart().length;
    const rawBody = untrimmedBody.trim();
    const bodyOffsetInMarkdown = block.start + leadingWhitespace;

    // Split into paragraphs while tracking each paragraph's ABSOLUTE offset in
    // `markdown` (not just relative to rawBody), so every paragraph can look
    // up its OWN citations by where their [E00x]/[N] marker actually landed
    // -- instead of every citation in the section being dumped onto the
    // first paragraph regardless of which sentence they belong to.
    const paragraphs = [];
    const paraSplitRegex = /\n\s*\n/g;
    let paraCursor = 0;
    let splitMatch;
    while ((splitMatch = paraSplitRegex.exec(rawBody)) !== null) {
      const chunk = rawBody.slice(paraCursor, splitMatch.index);
      if (chunk.trim()) {
        paragraphs.push({
          text: chunk.trim(),
          absStart: bodyOffsetInMarkdown + paraCursor,
          absEnd: bodyOffsetInMarkdown + splitMatch.index,
        });
      }
      paraCursor = splitMatch.index + splitMatch[0].length;
    }
    const tailChunk = rawBody.slice(paraCursor);
    if (tailChunk.trim()) {
      paragraphs.push({
        text: tailChunk.trim(),
        absStart: bodyOffsetInMarkdown + paraCursor,
        absEnd: bodyOffsetInMarkdown + rawBody.length,
      });
    }

    const citations = (result.citations || [])
      .filter((citation) => citation.review_char_start >= block.start && citation.review_char_start < block.end)
      .map((citation) => enrichCitation(citation, workspacePapers));

    const sentences = (paragraphs.length ? paragraphs : [{ text: rawBody, absStart: block.start, absEnd: block.end }])
      .map((para) => ({
        text: para.text,
        sentence_type: 'claim',
        citations: citations.filter(
          (c) => c.review_char_start >= para.absStart && c.review_char_start < para.absEnd,
        ),
      }));

    const uniqueEvidenceCount = new Set(citations.map((c) => c.evidence_id || c.id)).size;
    const uniquePaperCount = new Set(citations.map((c) => c.paper_id).filter(Boolean)).size;

    return {
      id: `fast-section-${index}`,
      title: block.title,
      coverage: {
        status: citations.length ? 'sufficient' : 'partial',
        reasons: [],
        evidence_count: uniqueEvidenceCount,
        paper_count: uniquePaperCount,
      },
      sentences,
    };
  });
}

/**
 * Builds comparison matrix rows with interactive evidence grounding for every cell.
 */
export function buildComparisonRows(evidenceProfile, workspacePapers, citations = [], reviewSections = []) {
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

  // Fast path stores verified narrative/citations rather than Legacy evidence
  // records. Populate matrix cells from the grounded section that cites paper.
  if (!evidenceProfile?.length) {
    for (const section of reviewSections || []) {
      const label = (section.title || '').toLowerCase();
      const field = label.includes('method') || label.includes('algorithm') || label.includes('phương pháp')
        ? 'method'
        : label.includes('limit') || label.includes('constraint') || label.includes('hạn chế')
          ? 'limitations'
          : label.includes('data') || label.includes('dataset') || label.includes('experiment') || label.includes('ứng dụng')
            ? 'dataset'
            : 'findings';
      for (const citation of section.sentences?.flatMap((sentence) => sentence.citations || []) || []) {
        const row = buckets.get(citation.paper_id);
        // Do not repeat writer prose for every cited paper. A matrix cell must
        // show source-derived text tied to that particular paper.
        const value = (citation.quoted_snippet || '').replace(/\s+/g, ' ').trim().slice(0, 280);
        if (row && value && !row.cells[field].value) {
          row.cells[field] = { value, quote: citation.quoted_snippet || value, citation };
          row[field] = value;
        }
      }
    }
  }

  return Array.from(buckets.values()).filter((row) =>
    Object.values(row.cells).some((cell) => cell.value)
  );
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

/**
 * Derives a human-facing citation-quality snapshot for a review.
 *
 * Faithfulness/Hallucination/citedParagraphs are computed straight from
 * `reviewSections` (the same paragraphs already rendered on screen) so this
 * always has a value -- when a session is reloaded from history or from a
 * status poll, only `review_markdown` + `citations` survive (no
 * diagnostics), so anything derived from the backend's own
 * CitationCoverageTelemetry (see
 * src/synthesis/fast_v2/citations/anthropic_citations.py::CitationCoverageTelemetry.to_dict)
 * would otherwise silently disappear on reload.
 *
 * `telemetry` (diagnostics.citation_coverage_telemetry, only present in the
 * direct /synthesis/execute response right after a run) is optional and
 * only backs two backend-only figures that cannot be recovered from the
 * saved citations alone: citation precision (valid vs. emitted handles --
 * invalid ones are already stripped from the saved text) and how many
 * claims Module 1's local Tier 1/2 pre-filter resolved without an LLM call.
 * Both read as null (rendered "—") once `telemetry` is unavailable, rather
 * than a stale or fabricated number.
 *
 * This is fast_v2's own measured coverage, NOT the Legacy Tri-Layer
 * Engine's /synthesis-sessions/{id}/quality endpoint -- that endpoint reads
 * SynthesisClaim rows the fast_v2 pipeline never writes, so it always
 * reports 0 claims for a fast_v2 session.
 */
export function computeCitationQuality(reviewSections, telemetry = null) {
  const allSentences = (reviewSections || []).flatMap((section) => section.sentences || []);
  const substantiveParagraphs = allSentences.length;
  if (!substantiveParagraphs) return null;

  const citedParagraphs = allSentences.filter((s) => (s.citations || []).length > 0).length;
  const uncited = substantiveParagraphs - citedParagraphs;
  const emitted = telemetry?.citation_markers_emitted || 0;
  const valid = telemetry?.valid_handles || 0;

  return {
    substantiveParagraphs,
    citedParagraphs,
    faithfulnessPct: Math.round((citedParagraphs / substantiveParagraphs) * 1000) / 10,
    hallucinationPct: Math.round((uncited / substantiveParagraphs) * 1000) / 10,
    precisionPct: telemetry && emitted > 0 ? Math.round((valid / emitted) * 1000) / 10 : null,
    tier1_2ResolvedClaims: telemetry ? (telemetry.tier1_2_resolved_claims || 0) : null,
    llmCallsSkipped: telemetry ? (telemetry.llm_calls_skipped_by_tier1_2 || 0) : null,
  };
}

export function tokenizeReviewCitations(review, citations) {
  const text = review || '';
  const tokens = [];
  const regex = /\[(?:E\d{3}|\d+)(?:,\s*(?:E\d{3}|\d+))*\]/g;
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
