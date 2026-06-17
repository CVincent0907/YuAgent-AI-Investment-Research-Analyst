import os
from typing import List, Dict, Any, Optional
from pypdf import PdfReader

class Document:
    """Represents a document chunk with page content and metadata."""
    def __init__(self, page_content: str, metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        meta_str = ", ".join(f"{k}={v}" for k, v in self.metadata.items())
        content_preview = self.page_content[:60].replace('\n', ' ')
        return f"Document(content_preview='{content_preview}...', {meta_str})"


class PDFParser:
    """Parses PDF documents and returns a list of Document objects (one per page)."""
    
    @staticmethod
    def parse(file_path: str) -> List[Document]:
        """Reads a PDF file and extracts text page-by-page.
        
        Args:
            file_path: The absolute or relative path to the PDF file.
            
        Returns:
            A list of Document objects with extracted text and metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
            
        documents = []
        filename = os.path.basename(file_path)
        
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        
        for page_idx, page in enumerate(reader.pages):
            page_number = page_idx + 1
            # Extract text from the page
            text = page.extract_text() or ""
            
            # Clean up double spacing or other common artifacts if desired
            text = text.strip()
            
            # Record metadata that will help the downstream agent reference the source
            metadata = {
                "source": filename,
                "path": os.path.abspath(file_path),
                "page": page_number,
                "total_pages": total_pages
            }
            
            documents.append(Document(page_content=text, metadata=metadata))
            
        return documents
