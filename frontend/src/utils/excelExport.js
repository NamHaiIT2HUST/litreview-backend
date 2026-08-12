import * as XLSX from 'xlsx';

export const exportPapersToExcel = (papers, filename = 'LitReview_Dataset.xlsx') => {
  if (!papers || papers.length === 0) return;

  const worksheetData = papers.map(p => ({
    "Mã Scholar": p.id,
    "Tiêu đề": p.title,
    "Tác giả": p.authors,
    "Tạp chí": p.journal,
    "Năm xuất bản": p.year,
    "Lượt trích dẫn": p.citation_count || p.citations,
    "DOI": p.doi,
    "Tóm tắt ngắn (TL;DR)": p.tldr,
    "Tóm tắt (Abstract)": p.abstract
  }));

  const worksheet = XLSX.utils.json_to_sheet(worksheetData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'LitReview_Dataset');
  XLSX.writeFile(workbook, filename);
};
