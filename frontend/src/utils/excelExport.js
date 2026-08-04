import * as XLSX from 'xlsx';

export const exportPapersToExcel = (papers, filename = 'LitReview_Dataset.xlsx') => {
  if (!papers || papers.length === 0) return;

  const worksheetData = papers.map(p => ({
    ID: p.id,
    Title: p.title,
    Authors: p.authors,
    Journal: p.journal,
    Year: p.year,
    Citations: p.citations,
    LitScore: p.litScore,
    DOI: p.doi,
    TLDR: p.tldr,
    Abstract: p.abstract
  }));

  const worksheet = XLSX.utils.json_to_sheet(worksheetData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'LitReview_Dataset');
  XLSX.writeFile(workbook, filename);
};
