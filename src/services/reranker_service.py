import os
import re

class RerankerService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RerankerService, cls).__new__(cls)
        return cls._instance

    def _get_model(self):
        if self._model is None:
            model_path = "./models/temp_bge-base"
            if os.path.exists(model_path):
                try:
                    import torch
                    from sentence_transformers import CrossEncoder
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    print(f"✅ Loading fine-tuned academic reranker from {model_path}...")
                    self._model = CrossEncoder(model_path, max_length=384, device=device)
                except Exception as e:
                    print(f"⚠️ Failed to load local CrossEncoder: {e}")
                    self._model = "fallback"
            else:
                self._model = "fallback"
        return self._model

    def rerank_papers(self, query: str, papers: list) -> list:
        """
        papers: List of dicts with 'id', 'title', 'abstract'
        Returns: List of papers with added 'relevance_score' and sorted.
        """
        if not papers:
            return []

        model = self._get_model()
        
        if model != "fallback":
            try:
                pairs = []
                for p in papers:
                    doc_text = f"{p.get('title', '')}. {p.get('abstract', '')}"
                    pairs.append([query, doc_text])
                
                scores = model.predict(pairs)
                scored_papers = []
                for i, p in enumerate(papers):
                    paper_copy = dict(p)
                    paper_copy['relevance_score'] = float(scores[i])
                    scored_papers.append(paper_copy)
                    
                scored_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
                return scored_papers
            except Exception as e:
                print(f"Reranker model inference failed, using heuristic: {e}")

        # Ultra-fast heuristic ranking based on query term overlap, title matches, and recency
        query_words = set(re.findall(r'\w+', query.lower()))
        scored_papers = []
        for p in papers:
            paper_copy = dict(p)
            title = str(p.get('title', '')).lower()
            abstract = str(p.get('abstract', '')).lower()
            
            title_hits = sum(2.0 for w in query_words if w in title)
            abstract_hits = sum(1.0 for w in query_words if w in abstract)
            
            score = title_hits * 3.0 + abstract_hits * 1.0
            paper_copy['relevance_score'] = float(score)
            scored_papers.append(paper_copy)

        scored_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_papers

reranker_service = RerankerService()
