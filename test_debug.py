import sys
import re

import fitz

doc = fitz.open('uploads/papers/586f7763-3a24-406d-802b-5ced623a8e91_s11370-024-00550-5.pdf')
page = doc[14]

def clean_word(w):
    return re.sub(r'\W+', '', w).lower()

search_text = "Intelligent Service Robotics (2024) 17:1091-1107 1105 76. Kim D, Oh N, Hwang D et al (2024) Lingo-space: language- conditioned incremental grounding for space. In: Proceedings of the AAAI conference on artificial intelligence (AAAI), pp 10314- 10322 77."
search_words = [clean_word(w) for w in search_text.split() if clean_word(w)]
page_words = page.get_text("words")

print("Search words:", search_words[:10], "... total:", len(search_words))

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

print(f"Max matches: {max_matches} out of {len(search_words)}")
print(f"Window bounds: start {best_start}, end {best_end}")

if max_matches > 0 and max_matches >= len(search_words) * 0.2:
    print(f"Success! Captured {(best_end - best_start + 1)} rects.")
else:
    print("Failed threshold")

