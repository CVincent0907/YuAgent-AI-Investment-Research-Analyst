import os
from dotenv import load_dotenv
from langsmith import traceable
from src.ingestion import PDFParser
from src.chunking import RecursiveTextSplitter
from src.embeddings.embedder import LocalEmbedder
from src.vectordb.chroma_client import ChromaVectorStore


@traceable(name="Ingest and Store PDF Action")
def ingest_and_store(pdf_path: str, persist_dir: str = ".chromadb", collection_name: str = "financial_rag"):
    """Parse a PDF, chunk it, embed the chunks, and upsert them into Chroma.
    Returns the ChromaVectorStore instance for later queries.
    """
    load_dotenv()
    print("\n--- Ingestion Phase ---\n")
    # Parse PDF
    print(f"Parsing PDF: {pdf_path}")
    documents = PDFParser.parse(pdf_path)
    print(f"Parsed {len(documents)} pages.")
    # Chunk text
    splitter = RecursiveTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} text chunks.")
    # Generate embeddings
    embedder = LocalEmbedder()
    embeddings = embedder.embed_documents(chunks)
    # Store in Chroma
    store = ChromaVectorStore(persist_dir=persist_dir, collection_name=collection_name)
    ids = store.upsert_documents(chunks, embeddings)
    print(f"Stored {len(ids)} vectors in Chroma collection '{collection_name}'.")
    return store
