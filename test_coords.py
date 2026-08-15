import sys
import json
from src.api.routes import get_evidence_coords, EvidenceCoordsRequest
import asyncio

async def test():
    req = EvidenceCoordsRequest(
        filename="586f7763-3a24-406d-802b-5ced623a8e91_s11370-024-00550-5.pdf",
        page=15,
        snippet="Intelligent Service Robotics (2024) 17:1091-1107 1105 76. Kim D, Oh N, Hwang D et al (2024) Lingo-space: language- conditioned incremental grounding for space. In: Proceedings of the AAAI conference on artificial intelligence (AAAI), pp 10314- 10322 77."
    )
    res = await get_evidence_coords(req)
    print("Rects found:", len(res.rects))
    if len(res.rects) == 0:
        import fitz
        doc = fitz.open('uploads/papers/586f7763-3a24-406d-802b-5ced623a8e91_s11370-024-00550-5.pdf')
        page = doc[14]
        words = page.get_text('words')
        print("Total words on page:", len(words))
        # Print a few words
        print("First 20 words:", [w[4] for w in words[:20]])
        
        # Test my logic manually
        import re
        def clean_word(w):
            return re.sub(r'\W+', '', w).lower()
        search_words = [clean_word(w) for w in req.snippet.split() if clean_word(w)]
        print("Search words:", search_words)
        print("Search word count:", len(search_words))

asyncio.run(test())
