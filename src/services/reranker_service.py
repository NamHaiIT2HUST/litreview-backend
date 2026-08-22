import os
import torch
from sentence_transformers import CrossEncoder

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
            # Fallback to HuggingFace if local model doesn't exist
            if not os.path.exists(model_path):
                print("⚠️ Local model not found. Loading base bge-reranker-base from HuggingFace.")
                model_path = "BAAI/bge-reranker-base"
            else:
                print(f"✅ Loading fine-tuned academic reranker from {model_path}...")
            
            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = CrossEncoder(model_path, max_length=384, device=device)
        return self._model

    def rerank_papers(self, query: str, papers: list) -> list:
        """
        papers: List of dicts with 'id', 'title', 'abstract'
        Returns: List of papers with added 'relevance_score' and sorted.
        """
        if not papers:
            return []

        model = self._get_model()
        
        # Prepare pairs: [query, title + abstract]
        pairs = []
        for p in papers:
            doc_text = f"{p.get('title', '')}. {p.get('abstract', '')}"
            pairs.append([query, doc_text])
        
        # Predict scores
        scores = model.predict(pairs)
        
        # Attach scores and sort
        scored_papers = []
        for i, p in enumerate(papers):
            paper_copy = dict(p)
            # Convert float32 to python float for JSON serialization
            paper_copy['relevance_score'] = float(scores[i])
            scored_papers.append(paper_copy)
            
        # Sort descending by score
        scored_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_papers

# Singleton instance
reranker_service = RerankerService()
