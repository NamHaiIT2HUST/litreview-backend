import sys

code = '''
        # If still empty, try robust word-level matching
        if not instances:
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
                            
                        # look ahead in search_words
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
                    # Collect bounding boxes for these words
                    for i in range(best_start, best_end + 1):
                        w = page_words[i]
                        rects.append(RectCoord(
                            x=w[0] / page_width,
                            y=w[1] / page_height,
                            width=(w[2] - w[0]) / page_width,
                            height=(w[3] - w[1]) / page_height
                        ))
                    
                    return EvidenceCoordsResponse(rects=rects)
'''

with open('src/api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        # If still empty, try even shorter
        if not instances and len(search_text) > 20:
            instances = page.search_for(search_text[:20])

        rects = []
        for inst in instances:
            rects.append(RectCoord(
                x=inst.x0 / page_width,
                y=inst.y0 / page_height,
                width=(inst.x1 - inst.x0) / page_width,
                height=(inst.y1 - inst.y0) / page_height
            ))'''

replacement = '''        # If still empty, try even shorter
        if not instances and len(search_text) > 20:
            instances = page.search_for(search_text[:20])

        rects = []
        for inst in instances:
            rects.append(RectCoord(
                x=inst.x0 / page_width,
                y=inst.y0 / page_height,
                width=(inst.x1 - inst.x0) / page_width,
                height=(inst.y1 - inst.y0) / page_height
            ))
''' + code

if target in content:
    content = content.replace(target, replacement)
    with open('src/api/routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Target not found")
