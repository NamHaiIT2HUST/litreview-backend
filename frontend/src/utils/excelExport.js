import * as XLSX from 'xlsx';

export const exportPapersToExcel = (papers, filename = 'LitReview_Dataset.xlsx') => {
  if (!papers || papers.length === 0) return;

  const worksheetData = papers.map(p => ({
    "Mã Scholar": p.id,
    "Tiêu đề": p.title,
    "Tác giả": Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || ''),
    "Tạp chí": p.journal || p.venue || '',
    "Năm xuất bản": p.year,
    "Lượt trích dẫn": p.citation_count || p.citations || 0,
    "DOI": p.doi || '',
    "Tóm tắt ngắn (TL;DR)": p.tldr || '',
    "Tóm tắt (Abstract)": p.abstract || ''
  }));

  const worksheet = XLSX.utils.json_to_sheet(worksheetData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'LitReview_Dataset');
  XLSX.writeFile(workbook, filename);
};

export const exportPapersToCsv = (papers, filename = 'LitReview_Dataset.csv') => {
  if (!papers || papers.length === 0) return;

  const worksheetData = papers.map(p => ({
    "Mã Scholar": p.id,
    "Tiêu đề": p.title,
    "Tác giả": Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors || ''),
    "Tạp chí": p.journal || p.venue || '',
    "Năm xuất bản": p.year,
    "Lượt trích dẫn": p.citation_count || p.citations || 0,
    "DOI": p.doi || '',
    "Tóm tắt ngắn (TL;DR)": p.tldr || '',
    "Tóm tắt (Abstract)": p.abstract || ''
  }));

  const worksheet = XLSX.utils.json_to_sheet(worksheetData);
  const csvOutput = XLSX.utils.sheet_to_csv(worksheet);
  const blob = new Blob(["\ufeff" + csvOutput], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
