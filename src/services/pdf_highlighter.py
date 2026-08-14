import fitz
import re
import os
from typing import List, Dict, Optional

def normalize_text(text: str) -> str:
    """Normalize whitespace and newlines for easier matching."""
    return re.sub(r'\s+', ' ', text).strip()

def get_evidence_bounding_boxes(pdf_path: str, page_num: int, text: str) -> List[Dict[str, float]]:
    """
    Finds the text in the specified PDF page and returns a list of bounding boxes
    as percentages [0, 1] of the page width and height.
    Returns: [{"x": float, "y": float, "width": float, "height": float}, ...]
    """
    if not os.path.exists(pdf_path):
        return []
        
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            return []
            
        page = doc[page_num - 1]
        
        # 1. Try exact match
        quads = page.search_for(text, quads=True)
        
        # 2. Try normalized match if exact fails
        if not quads:
            norm_text = normalize_text(text)
            quads = page.search_for(norm_text, quads=True)
            
        # 3. If still fails, break into chunks (e.g., lines or phrases) and match
        if not quads:
            chunks = [c.strip() for c in text.split('\n') if len(c.strip()) > 10]
            if not chunks:
                words = norm_text.split()
                chunks = [' '.join(words[i:i+7]) for i in range(0, len(words), 7)]
                
            for chunk in chunks:
                chunk_quads = page.search_for(chunk, quads=True)
                if chunk_quads:
                    quads.extend(chunk_quads)

        rects = []
        page_width = page.rect.width
        page_height = page.rect.height
        
        for q in quads:
            rect = q.rect
            rects.append({
                "x": rect.x0 / page_width,
                "y": rect.y0 / page_height,
                "width": rect.width / page_width,
                "height": rect.height / page_height
            })
            
        doc.close()
        return rects
    except Exception as e:
        print(f"Error extracting bounding boxes: {e}")
        return []
