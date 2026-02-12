from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingService:
    def __init__(self):
        # Load the model. Ideally this should be a singleton or loaded at startup.
        # For simplicity in this module, we initialize it here, but in a larger app
        # this might be dependency injected as a singleton.
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embedding(self, text: str) -> List[float]:
        if not text:
            return []
        
        # logical optimization: truncate text if too long for the model? 
        # all-MiniLM-L6-v2 has a max sequence length (usually 256 or 384 tokens).
        # We'll just let the library handle truncation or we could do it manually.
        # For resume summaries, it might fit.
        
        embeddings = self.model.encode(text)
        return embeddings.tolist()
