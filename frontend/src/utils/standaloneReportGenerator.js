/**
 * Standalone HTML Report & Jupyter Notebook (.ipynb) Generator for EDA Analysis
 * Provides continuous paper document layout, direct html2pdf export, and clean typography.
 */

/**
 * Sanitizes text to prevent broken character glitches (e.g. unicode replacement chars).
 */
function sanitizeText(str) {
  if (!str) return '';
  return String(str)
    .replace(/\uFFFD/g, 'ó') // Fix replacement character for common Vietnamese vowels if corrupted
    .replace(/C\s*\s*TƯƠNG/gi, 'CÓ TƯƠNG')
    .replace(/C/g, 'Có');
}

/**
 * Converts a simple markdown string to clean HTML.
 */
function markdownToHtml(md) {
  if (!md) return '';
  let html = sanitizeText(md)
    // Escape HTML special chars except those needed
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3 class="report-h3">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 class="report-h2">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 class="report-h1">$1</h1>');

  // Bold & Italic
  html = html.replace(/\*\*\*(.*?)\*\*\*/gim, '<strong><em>$1</em></strong>');
  html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

  // Inline code
  html = html.replace(/`([^`]+)`/gim, '<code class="inline-code">$1</code>');

  // Blockquotes
  html = html.replace(/^\> (.*$)/gim, '<blockquote class="report-quote">$1</blockquote>');

  // Unordered list items
  html = html.replace(/^\s*[\-\*]\s+(.*$)/gim, '<li class="report-li">$1</li>');
  html = html.replace(/(<li class="report-li">.*<\/li>\n?)+/gim, '<ul class="report-ul">$&</ul>');

  // Ordered list items
  html = html.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="report-oli">$1</li>');
  html = html.replace(/(<li class="report-oli".*<\/li>\n?)+/gim, '<ol class="report-ol">$&</ol>');

  // Markdown Tables
  const tableRegex = /((?:\|.+?\|\r?\n)+)/g;
  html = html.replace(tableRegex, (tableText) => {
    const lines = tableText.trim().split('\n').map(l => l.trim()).filter(Boolean);
    if (lines.length < 2) return tableText;
    
    let tableHtml = '<div class="table-wrapper"><table class="report-table">';
    lines.forEach((line, idx) => {
      if (line.includes('---')) return;
      const cells = line.split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
      if (idx === 0) {
        tableHtml += '<thead><tr>' + cells.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
      } else {
        tableHtml += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
      }
    });
    tableHtml += '</tbody></table></div>';
    return tableHtml;
  });

  // Paragraphs
  const paragraphs = html.split(/\n{2,}/);
  html = paragraphs.map(p => {
    p = p.trim();
    if (!p) return '';
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<blockquote') || p.startsWith('<div class="table-wrapper"')) {
      return p;
    }
    return `<p class="report-p">${p.replace(/\n/g, '<br/>')}</p>`;
  }).join('\n');

  return html;
}

/**
 * Compiles a complete standalone HTML document with unified document flow and embedded PDF generator.
 */
export function generateStandaloneHTMLReport({ message, filename = 'dataset.csv', title = 'Báo Cáo Phân Tích Khám Phá Dữ Liệu (EDA)' }) {
  const timestamp = new Date().toLocaleString('vi-VN', { dateStyle: 'full', timeStyle: 'medium' });
  const rawText = message?.text || '';
  const blockOutputs = message?.block_outputs || [];
  const kpis = message?.kpis || [];
  const pythonCode = message?.python_code || '';
  const figures = message?.figures || [];

  // Parse text into interleaved parts
  const parts = rawText.split(/```(?:python|py)\s*[\r\n]+([\s\S]*?)```/i);
  let documentContentHtml = '';

  parts.forEach((part, index) => {
    if (index % 2 === 0) {
      // Narrative text
      if (part.trim()) {
        documentContentHtml += `<div class="article-text-block">${markdownToHtml(part)}</div>`;
      }
    } else {
      // Notebook cell: Code block + Output block (unified container)
      const blockIndex = Math.floor(index / 2);
      const output = blockOutputs[blockIndex];
      const codeEscaped = sanitizeText(part)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

      documentContentHtml += `
        <div class="notebook-cell" id="cell-${blockIndex + 1}">
          <div class="cell-input">
            <div class="cell-header">
              <span class="cell-tag">In [${blockIndex + 1}]:</span>
              <span class="cell-lang">Python</span>
              <button class="copy-btn" onclick="copyCode(this)">Sao chép mã</button>
            </div>
            <pre class="code-pre"><code>${codeEscaped}</code></pre>
          </div>
      `;

      if (output && (output.stdout || (output.figures && output.figures.length > 0))) {
        documentContentHtml += `<div class="cell-output">`;
        
        if (output.stdout) {
          const stdoutEscaped = sanitizeText(output.stdout)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
          documentContentHtml += `
            <div class="stdout-block">
              <div class="output-tag">Out [${blockIndex + 1}]:</div>
              <pre class="stdout-pre"><code>${stdoutEscaped}</code></pre>
            </div>
          `;
        }

        if (output.figures && output.figures.length > 0) {
          documentContentHtml += `
            <div class="figures-flow">
              ${output.figures.map((fig, fIdx) => `
                <div class="figure-frame">
                  <img src="${fig}" alt="Figure ${blockIndex + 1}.${fIdx + 1}" loading="lazy" />
                  <div class="figure-label">Hình #${blockIndex + 1}.${fIdx + 1} — Biểu đồ phân tích dữ liệu</div>
                </div>
              `).join('')}
            </div>
          `;
        }

        documentContentHtml += `</div>`; // end cell-output
      }

      documentContentHtml += `</div>`; // end notebook-cell
    }
  });

  // Fallback for non-interleaved figures
  if (figures.length > 0 && (!blockOutputs || blockOutputs.length === 0)) {
    documentContentHtml += `
      <div class="figures-gallery">
        <h3 class="report-h3">Đồ thị Trực quan hóa Dữ liệu Thực nghiệm</h3>
        <div class="figures-flow">
          ${figures.map((fig, fIdx) => `
            <div class="figure-frame">
              <img src="${fig}" alt="Figure ${fIdx + 1}" loading="lazy" />
              <div class="figure-label">Hình #${fIdx + 1} — Biểu đồ phân tích</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // KPIs Header
  let kpisHtml = '';
  if (kpis && kpis.length > 0) {
    kpisHtml = `
      <div class="kpi-banner">
        <div class="kpi-banner-title">📊 Các Chỉ Số Thống Kê Trọng Yếu (Key Findings)</div>
        <div class="kpi-flex-container">
          ${kpis.map(kpi => `
            <div class="kpi-pill">
              <div class="kpi-label">${sanitizeText(kpi.label || '')}</div>
              <div class="kpi-value">${sanitizeText(String(kpi.value || ''))}</div>
              ${kpi.subtext ? `<div class="kpi-subtext">${sanitizeText(kpi.subtext)}</div>` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Technical Appendix (Full Python Script)
  let appendixHtml = '';
  if (pythonCode) {
    const fullCodeEscaped = sanitizeText(pythonCode)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    appendixHtml = `
      <section class="appendix-block" id="technical-appendix">
        <h2 class="report-h2">Phụ lục Kỹ thuật: Mã nguồn Python Tổng hợp</h2>
        <p class="report-p">Mã nguồn dưới đây tập hợp toàn bộ các bước xử lý và trực quan hóa dữ liệu. Bạn có thể sao chép để chạy độc lập trong môi trường Python, Google Colab hoặc Jupyter Notebook.</p>
        <div class="notebook-cell">
          <div class="cell-input">
            <div class="cell-header">
              <span class="cell-tag">Script:</span>
              <span class="cell-lang">Full EDA Pipeline</span>
              <button class="copy-btn" onclick="copyCode(this)">Sao chép toàn bộ</button>
            </div>
            <pre class="code-pre"><code>${fullCodeEscaped}</code></pre>
          </div>
        </div>
      </section>
    `;
  }

  return `<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title} - ${filename}</title>
  <!-- Google Fonts with full Vietnamese subset support -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  
  <!-- html2pdf.js for client-side PDF generation -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>

  <style>
    :root {
      --bg-page: #f1f5f9;
      --bg-paper: #ffffff;
      --border-light: #e2e8f0;
      --border-dark: #cbd5e1;
      --text-main: #0f172a;
      --text-body: #334155;
      --text-muted: #64748b;
      --accent: #2563eb;
      --accent-soft: #eff6ff;
      --code-bg: #0f172a;
      --code-text: #f8fafc;
      --output-bg: #f8fafc;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      font-family: 'Plus Jakarta Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background-color: var(--bg-page);
      color: var(--text-main);
      line-height: 1.7;
      font-size: 15px;
      -webkit-font-smoothing: antialiased;
    }

    /* Outer Wrapper */
    .page-wrapper {
      max-width: 980px;
      margin: 32px auto;
      padding: 0 16px 64px 16px;
    }

    /* Action Bar (Screen Only) */
    .top-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      padding: 12px 20px;
      background: #ffffff;
      border: 1px solid var(--border-light);
      border-radius: 12px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .top-controls-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .btn-group { display: flex; gap: 8px; }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border-dark);
      background: #ffffff;
      color: var(--text-main);
      transition: all 0.15s ease;
      text-decoration: none;
    }
    .btn:hover { background: var(--accent-soft); border-color: var(--accent); color: var(--accent); }
    .btn-primary { background: var(--accent); color: #ffffff; border-color: var(--accent); }
    .btn-primary:hover { background: #1d4ed8; color: #ffffff; }

    /* Single Unified Paper Document */
    .report-paper {
      background: var(--bg-paper);
      border: 1px solid var(--border-light);
      border-radius: 16px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      padding: 48px 48px;
    }

    /* Document Header */
    .doc-header {
      border-bottom: 2px solid var(--border-light);
      padding-bottom: 24px;
      margin-bottom: 28px;
    }
    .doc-badge {
      display: inline-block;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      padding: 4px 12px;
      border-radius: 9999px;
      margin-bottom: 12px;
      text-transform: uppercase;
    }
    .doc-title {
      font-size: 26px;
      font-weight: 800;
      color: var(--text-main);
      letter-spacing: -0.02em;
      margin-bottom: 12px;
    }
    .doc-meta-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 13px;
      color: var(--text-muted);
      margin-top: 12px;
    }
    .meta-item strong { color: var(--text-main); }

    /* KPI Banner (Balanced flex container) */
    .kpi-banner {
      background: #f8fafc;
      border: 1px solid var(--border-light);
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 32px;
    }
    .kpi-banner-title {
      font-size: 12px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 14px;
    }
    .kpi-flex-container {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
    .kpi-pill {
      flex: 1 1 180px;
      background: #ffffff;
      border: 1px solid var(--border-light);
      border-radius: 10px;
      padding: 12px 16px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .kpi-label { font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; }
    .kpi-value { font-size: 20px; font-weight: 800; color: var(--accent); margin: 2px 0; }
    .kpi-subtext { font-size: 11.5px; color: var(--text-body); }

    /* Continuous Flow Typography */
    .article-text-block {
      margin-bottom: 20px;
    }
    .report-h1 {
      font-size: 20px;
      font-weight: 800;
      color: var(--text-main);
      margin: 32px 0 14px 0;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border-light);
    }
    .report-h2 {
      font-size: 17px;
      font-weight: 700;
      color: var(--text-main);
      margin: 24px 0 10px 0;
    }
    .report-h3 {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-main);
      margin: 18px 0 8px 0;
    }
    .report-p {
      color: var(--text-body);
      margin-bottom: 14px;
      text-align: justify;
    }
    .report-quote {
      border-left: 3px solid var(--accent);
      padding: 8px 16px;
      background: var(--accent-soft);
      color: var(--text-body);
      border-radius: 0 8px 8px 0;
      margin: 14px 0;
      font-style: italic;
    }
    .report-ul, .report-ol {
      margin: 8px 0 16px 24px;
      color: var(--text-body);
    }
    .report-li, .report-oli { margin-bottom: 6px; }
    .inline-code {
      font-family: 'JetBrains Mono', monospace;
      background: #f1f5f9;
      color: var(--accent);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 13px;
    }

    /* Tables */
    .table-wrapper {
      margin: 16px 0;
      border: 1px solid var(--border-light);
      border-radius: 8px;
      overflow-x: auto;
    }
    .report-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .report-table th {
      background: #f8fafc;
      color: var(--text-main);
      font-weight: 700;
      padding: 8px 12px;
      border-bottom: 1px solid var(--border-light);
      text-align: left;
    }
    .report-table td {
      padding: 8px 12px;
      border-bottom: 1px solid var(--border-light);
      color: var(--text-body);
    }
    .report-table tr:last-child td { border-bottom: none; }

    /* Notebook Cell (Integrated Code + Output) */
    .notebook-cell {
      border: 1px solid var(--border-light);
      border-radius: 10px;
      overflow: hidden;
      margin: 20px 0 24px 0;
      background: var(--code-bg);
      box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    .cell-input {
      background: var(--code-bg);
    }
    .cell-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 14px;
      background: rgba(255,255,255,0.05);
      border-bottom: 1px solid rgba(255,255,255,0.08);
    }
    .cell-tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      color: #38bdf8;
    }
    .cell-lang {
      font-size: 11px;
      color: #94a3b8;
      font-family: 'JetBrains Mono', monospace;
    }
    .copy-btn {
      background: rgba(255,255,255,0.1);
      border: none;
      color: #cbd5e1;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      cursor: pointer;
    }
    .copy-btn:hover { background: rgba(255,255,255,0.2); color: #fff; }
    .code-pre {
      padding: 14px 16px;
      margin: 0;
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: var(--code-text);
      line-height: 1.5;
      overflow-x: auto;
    }

    /* Output Section */
    .cell-output {
      background: var(--output-bg);
      border-top: 1px solid var(--border-light);
      padding: 16px 18px;
    }
    .stdout-block {
      margin-bottom: 12px;
    }
    .output-tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 11px;
      font-weight: 700;
      color: #dc2626;
      margin-bottom: 4px;
    }
    .stdout-pre {
      background: #ffffff;
      border: 1px solid var(--border-light);
      border-radius: 6px;
      padding: 10px 14px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      color: var(--text-body);
      overflow-x: auto;
    }

    /* Figures Flow */
    .figures-flow {
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-top: 10px;
    }
    .figure-frame {
      background: #ffffff;
      border: 1px solid var(--border-light);
      border-radius: 8px;
      padding: 12px;
      text-align: center;
    }
    .figure-frame img {
      max-width: 100%;
      height: auto;
      border-radius: 6px;
      display: block;
      margin: 0 auto;
    }
    .figure-label {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 8px;
      font-weight: 600;
    }

    /* Appendix */
    .appendix-block {
      border-top: 2px solid var(--border-light);
      margin-top: 40px;
      padding-top: 28px;
    }

    .doc-footer {
      text-align: center;
      margin-top: 36px;
      font-size: 12px;
      color: var(--text-muted);
      border-top: 1px solid var(--border-light);
      padding-top: 16px;
    }

    /* Print & PDF Specific Optimization */
    @media print {
      body { background: #ffffff !important; font-size: 11pt !important; }
      .page-wrapper { max-width: 100% !important; margin: 0 !important; padding: 0 !important; }
      .top-controls { display: none !important; }
      .report-paper {
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
      }
      .notebook-cell {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        page-break-inside: avoid !important;
      }
      .cell-input { background: #f8fafc !important; }
      .code-pre code { color: #0f172a !important; }
      .cell-header { background: #e2e8f0 !important; border-bottom: 1px solid #cbd5e1 !important; }
      .copy-btn { display: none !important; }
      .figure-frame { page-break-inside: avoid !important; border: 1px solid #cbd5e1 !important; }
      .figure-frame img { max-height: 450px !important; }
      .report-h1, .report-h2 { page-break-after: avoid !important; }
      @page {
        size: A4 portrait;
        margin: 15mm 15mm 20mm 15mm;
      }
    }
  </style>
</head>
<body>
  <div class="page-wrapper">
    <!-- Top Action Controls (Excluded in print/PDF) -->
    <div class="top-controls">
      <div class="top-controls-title">Công cụ xuất bản báo cáo</div>
      <div class="btn-group">
        <button class="btn btn-primary" id="btn-pdf" onclick="exportToPDF()">📄 Tải File PDF (Chuẩn A4)</button>
        <button class="btn" onclick="window.print()">🖨️ In trang</button>
      </div>
    </div>

    <!-- Main Unified Printable Paper Document -->
    <article class="report-paper" id="report-document">
      <header class="doc-header">
        <div class="doc-badge">📊 Báo Cáo Phân Tích Dữ Liệu</div>
        <h1 class="doc-title">${title}</h1>
        <div class="doc-meta-grid">
          <div class="meta-item">📁 <strong>Tập dữ liệu:</strong> ${filename}</div>
          <div class="meta-item">🕒 <strong>Thời gian xuất:</strong> ${timestamp}</div>
          <div class="meta-item">🤖 <strong>Công cụ:</strong> AI Data Science Workspace</div>
        </div>
      </header>

      ${kpisHtml}

      <main class="doc-content">
        ${documentContentHtml}
      </main>

      ${appendixHtml}

      <footer class="doc-footer">
        Báo cáo phân tích dữ liệu tự động — AI Data Science Workspace
      </footer>
    </article>
  </div>

  <script>
    function copyCode(btn) {
      const pre = btn.closest('.notebook-cell').querySelector('pre code');
      if (pre) {
        navigator.clipboard.writeText(pre.innerText).then(() => {
          const originalText = btn.innerText;
          btn.innerText = 'Đã chép!';
          setTimeout(() => { btn.innerText = originalText; }, 2000);
        });
      }
    }

    function exportToPDF() {
      const element = document.getElementById('report-document');
      const btn = document.getElementById('btn-pdf');
      const originalText = btn.innerText;
      
      btn.innerText = '⏳ Đang khởi tạo PDF...';
      btn.disabled = true;

      const opt = {
        margin:       [12, 12, 16, 12],
        filename:     '${filename ? filename.replace(/\.[^/.]+$/, '') : 'dataset'}_Bao_Cao_EDA.pdf',
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, letterRendering: true },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
      };

      html2pdf().set(opt).from(element).save().then(() => {
        btn.innerText = originalText;
        btn.disabled = false;
      }).catch(err => {
        console.error('PDF export error:', err);
        btn.innerText = originalText;
        btn.disabled = false;
        // Fallback to window.print() if html2pdf fails
        window.print();
      });
    }
  </script>
</body>
</html>`;
}

/**
 * Opens a compiled standalone HTML report in a new browser tab.
 */
export function openReportInNewTab(htmlString) {
  const blob = new Blob([htmlString], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

/**
 * Triggers a client-side file download of the standalone HTML report.
 */
export function downloadHTMLReport(htmlString, filename = 'Bao_cao_EDA.html') {
  const cleanName = filename.endsWith('.html') ? filename : `${filename}.html`;
  const blob = new Blob([htmlString], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = cleanName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

/**
 * Builds and downloads a standard Jupyter Notebook (.ipynb) JSON file.
 */
export function downloadJupyterNotebook(message, filename = 'eda_notebook.ipynb') {
  const rawText = message?.text || '';
  const blockOutputs = message?.block_outputs || [];
  const parts = rawText.split(/```(?:python|py)\s*[\r\n]+([\s\S]*?)```/i);
  
  const cells = [];

  parts.forEach((part, index) => {
    if (index % 2 === 0) {
      if (part.trim()) {
        cells.push({
          cell_type: 'markdown',
          metadata: {},
          source: sanitizeText(part).split('\n').map(l => l + '\n')
        });
      }
    } else {
      const blockIndex = Math.floor(index / 2);
      const output = blockOutputs[blockIndex];
      const notebookOutputs = [];

      if (output) {
        if (output.stdout) {
          notebookOutputs.push({
            output_type: 'stream',
            name: 'stdout',
            text: sanitizeText(output.stdout).split('\n').map(l => l + '\n')
          });
        }
        if (output.figures && output.figures.length > 0) {
          output.figures.forEach(fig => {
            const base64Data = fig.replace(/^data:image\/png;base64,/, '');
            notebookOutputs.push({
              output_type: 'display_data',
              data: {
                'image/png': base64Data,
                'text/plain': ['<Figure size>']
              },
              metadata: {}
            });
          });
        }
      }

      cells.push({
        cell_type: 'code',
        execution_count: blockIndex + 1,
        metadata: {},
        source: sanitizeText(part).split('\n').map(l => l + '\n'),
        outputs: notebookOutputs
      });
    }
  });

  const notebookJson = {
    cells,
    metadata: {
      kernelspec: {
        display_name: 'Python 3',
        language: 'python',
        name: 'python3'
      },
      language_info: {
        codemirror_mode: { name: 'ipython', version: 3 },
        file_extension: '.py',
        mimetype: 'text/x-python',
        name: 'python',
        nbconvert_exporter: 'python',
        pygments_lexer: 'ipython3',
        version: '3.10.0'
      }
    },
    nbformat: 4,
    nbformat_minor: 4
  };

  const cleanName = filename.endsWith('.ipynb') ? filename : `${filename}.ipynb`;
  const blob = new Blob([JSON.stringify(notebookJson, null, 2)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = cleanName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
