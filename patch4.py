import sys
import re

with open('src/api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the whole get_evidence_coords body
start_idx = content.find('async def get_evidence_coords(')
end_idx = content.find('def _run_synthesis_fallback', start_idx)

if start_idx != -1 and end_idx != -1:
    replacement = '''async def get_evidence_coords(
    request: EvidenceCoordsRequest,
) -> EvidenceCoordsResponse:
    \"\"\"Find text coordinates in PDF for highlighting.\"\"\"
    import os
    import pymupdf as fitz
    import logging
    
    file_path = os.path.join("uploads", "papers", request.filename)
    if not os.path.exists(file_path):
        return EvidenceCoordsResponse(rects=[])
    
    try:
        doc = fitz.open(file_path)
        page_index = max(0, request.page - 1)
        if page_index >= len(doc):
            return EvidenceCoordsResponse(rects=[])
            
        page = doc[page_index]
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        search_text = request.snippet.strip()
        rects = []
        
        # Robust word-level matching
        import re
        def clean_word(w):
            return re.sub(r'\\W+', '', w).lower()

        search_words = [clean_word(w) for w in search_text.split() if clean_word(w)]
        page_words = page.get_text("words")
        
        if search_words and page_words:
            best_start = 0
            best_end = 0
            max_matches = -1
            
            window_size = min(len(search_words) + 15, len(page_words))
            
            for i in range(len(page_words) - window_size + 1):
                p_ptr = i
                s_ptr = 0
                matches = 0
                while p_ptr < i + window_size and s_ptr < len(search_words):
                    cw = clean_word(page_words[p_ptr][4])
                    if not cw:
                        p_ptr += 1
                        continue
                        
                    for lookahead in range(4):
                        if s_ptr + lookahead < len(search_words) and cw == search_words[s_ptr + lookahead]:
                            matches += 1
                            s_ptr += lookahead + 1
                            break
                    p_ptr += 1
                
                if matches > max_matches:
                    max_matches = matches
                    best_start = i
                    best_end = p_ptr - 1

            if max_matches > 0 and max_matches >= len(search_words) * 0.2:
                for i in range(best_start, best_end + 1):
                    w = page_words[i]
                    rects.append(RectCoord(
                        x=w[0] / page_width,
                        y=w[1] / page_height,
                        width=(w[2] - w[0]) / page_width,
                        height=(w[3] - w[1]) / page_height
                    ))
        
        return EvidenceCoordsResponse(rects=rects)
    except Exception as e:
        logging.getLogger(__name__).error("Error finding coords: %s", e)
        return EvidenceCoordsResponse(rects=[])

# ──────────────────────────────────────────────────────────────────────────────
# Synthesis endpoints (evidence-first, async job)
# ──────────────────────────────────────────────────────────────────────────────

async '''
    # Replace from start_idx to end_idx
    content = content[:start_idx] + replacement + content[end_idx+6:]
    with open('src/api/routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Not found")
