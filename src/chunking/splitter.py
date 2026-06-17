import re
from typing import List, Optional
from src.ingestion import Document

class RecursiveTextSplitter:
    """Splits a document's text recursively using a list of separators.
    
    This is highly educational and mimics how production RAG splitters (like
    LangChain's RecursiveCharacterTextSplitter) keep semantically related
    sentences/paragraphs together.
    """
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Default separators go from largest semantic boundaries (paragraphs) to smallest (characters)
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Splits a list of Documents into smaller chunk Documents."""
        split_docs = []
        for doc in documents:
            chunks = self.split_text(doc.page_content)
            for idx, chunk in enumerate(chunks):
                # Copy original metadata and add chunking details
                meta = doc.metadata.copy()
                meta["chunk_index"] = idx
                split_docs.append(Document(page_content=chunk, metadata=meta))
        return split_docs

    def split_text(self, text: str) -> List[str]:
        """Splits input text recursively based on chunk size and overlap."""
        return self._split_text(text, self.separators)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursive splitting implementation."""
        # If the text is already small enough, return it
        if len(text) <= self.chunk_size:
            return [text]

        # Get the current separator to try
        if not separators:
            # If no separators left, force chunking by character count
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = separators[0]
        next_separators = separators[1:]

        # Split the text by the current separator
        if separator == "":
            # Character-by-character split
            splits = list(text)
        else:
            # Split and retain separator positions where possible
            splits = text.split(separator)

        # Re-merge the splits into chunks of correct size
        chunks = []
        current_chunk = []
        current_length = 0

        for split in splits:
            # If a single split itself is larger than chunk_size, recursively split it using next separators
            if len(split) > self.chunk_size:
                # Flush the current chunk first
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Recursively split the long block
                sub_splits = self._split_text(split, next_separators)
                chunks.extend(sub_splits)
                continue

            # Check if adding this split exceeds the chunk size
            # Account for the separator length when joining
            join_len = len(separator) if current_chunk else 0
            if current_length + len(split) + join_len > self.chunk_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                
                # Create overlap: keep recent splits that fit within chunk_overlap
                overlap_chunk = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    s_join_len = len(separator) if overlap_chunk else 0
                    if overlap_len + len(s) + s_join_len <= self.chunk_overlap:
                        overlap_chunk.insert(0, s)
                        overlap_len += len(s) + s_join_len
                    else:
                        break
                
                current_chunk = overlap_chunk
                current_length = overlap_len

            current_chunk.append(split)
            current_length += len(split) + (len(separator) if len(current_chunk) > 1 else 0)

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        return chunks
