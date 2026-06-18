import os
import uuid
import chromadb
from typing import List, Dict, Any, Tuple, Optional
from src.ingestion import Document

class ChromaVectorStore:
    """Manages index lifecycle and document storage/retrieval in Chroma DB."""
    
    def __init__(self, persist_dir: str = ".chromadb", collection_name: str = "financial_rag"):
        """Initializes the Chroma persistent client.
        
        Args:
            persist_dir: Directory to save the database files.
            collection_name: The name of the collection.
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        
        # Initialize persistent chroma client
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def upsert_documents(self, documents: List[Document], embeddings: List[List[float]]) -> List[str]:
        """Upserts documents and their corresponding vector embeddings into Chroma.
        
        Args:
            documents: List of Document chunks.
            embeddings: List of float embeddings corresponding to each document.
            
        Returns:
            List of generated string IDs for the upserted vectors.
        """
        if len(documents) != len(embeddings):
            raise ValueError("The number of documents must match the number of embeddings.")
            
        ids = []
        metadatas = []
        contents = []
        
        for doc in documents:
            doc_id = str(uuid.uuid4())
            ids.append(doc_id)
            metadatas.append(doc.metadata)
            contents.append(doc.page_content)
            
        print(f"Upserting {len(ids)} documents into Chroma collection '{self.collection_name}'...")
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=contents
        )
        print("Upsert complete.")
        return ids

    def query(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[Document, float]]:
        """Searches Chroma for top_k similar vector chunks.
        
        Args:
            query_embedding: The query vector embedding.
            top_k: Number of documents to retrieve.
            
        Returns:
            A list of tuples (Document, score) of matches.
        """
        response = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        results = []
        
        # Parse Chroma response
        if response and "documents" in response and response["documents"]:
            docs = response["documents"][0]
            metadatas = response["metadatas"][0] if "metadatas" in response else [{}] * len(docs)
            distances = response["distances"][0] if "distances" in response else [0.0] * len(docs)
            
            for content, meta, dist in zip(docs, metadatas, distances):
                # Note: Chroma distance ranges vary, but usually lower distance is more similar (e.g., Cosine distance).
                # Convert distance to a similarity score if cosine (1 - distance) or output raw distance
                similarity_score = 1.0 - dist if dist is not None else 0.0
                doc = Document(page_content=content, metadata=meta)
                results.append((doc, similarity_score))
                
        return results
