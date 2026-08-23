/**
 * mathUtils.js
 * Comprehensive normalization for LaTeX math expressions and citation tags
 * to ensure seamless rendering with react-markdown, remark-math, and rehype-katex.
 */

export function formatMathAndMarkdown(text) {
  if (!text || typeof text !== 'string') return '';

  const codeBlocks = [];
  
  // 1. Protect fenced code blocks (``` ... ```)
  let formatted = text.replace(/```[\s\S]*?```/g, (match) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(match);
    return placeholder;
  });

  // 2. Protect inline code (` ... `)
  formatted = formatted.replace(/`[^`\n]+`/g, (match) => {
    const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
    codeBlocks.push(match);
    return placeholder;
  });

  // 3. Convert Display / Block LaTeX: \\[ ... \\] or \[ ... \] -> $$ ... $$
  formatted = formatted.replace(/\\+\[([\s\S]*?)\\+\]/g, (match, eq) => {
    return `\n\n$$\n${eq.trim()}\n$$\n\n`;
  });

  // 4. Convert Inline LaTeX: \\( ... \\) or \( ... \) -> $ ... $
  formatted = formatted.replace(/\\+\(([\s\S]*?)\\+\)/g, (match, eq) => {
    return `$${eq.trim()}$`;
  });

  // 5. Expand multi-citations: [1, 2] or [5, 4] -> [5][4]
  formatted = formatted.replace(/\[([\d\s,]+)\]/g, (match, inner) => {
    const nums = inner.split(',').map(n => n.trim()).filter(n => /^\d+$/.test(n));
    if (nums.length > 1) {
      return nums.map(n => `[${n}]`).join('');
    }
    return match;
  });

  // 6. Linkify citation tags [1] -> [[1]](#cite-1)
  // Ensure we don't double linkify or match inside markdown links
  formatted = formatted.replace(/(?<!!)(?<!\[)\[(\d+)\](?!\]|\()/g, '[[$1]](#cite-$1)');

  // 7. Restore protected code blocks
  codeBlocks.forEach((code, idx) => {
    formatted = formatted.replace(`__CODE_BLOCK_${idx}__`, code);
  });

  return formatted;
}
