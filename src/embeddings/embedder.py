from typing import List
from sentence_transformers import SentenceTransformer
from src.ingestion import Document

class LocalEmbedder:
    """Generates text embeddings locally using sentence-transformers models."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initializes the local embedder model.
        
        Args:
            model_name: The name of the SentenceTransformer model to load.
        """
        self.model_name = model_name
        # Loads model weights locally. It will download the weights on first execution.
        self.model = SentenceTransformer(model_name)
        
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates list of float embeddings for a list of raw text strings.
        
        Args:
            texts: List of text strings to embed.
            
        Returns:
            List of embeddings (each embedding is a list of floats).
        """
        embeddings = self.model.encode(texts, show_progress_bar=False)
        # Convert numpy arrays to standard python float lists
        return [em.tolist() for em in embeddings]

    def embed_documents(self, documents: List[Document]) -> List[List[float]]:
        """Generates embeddings for a list of Document objects using page_content.
        
        Args:
            documents: List of Document objects.
            
        Returns:
            List of embeddings corresponding to each document chunk.
        """
        texts = [doc.page_content for doc in documents]
        return self.embed_texts(texts)
