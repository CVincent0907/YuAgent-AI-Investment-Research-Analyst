import os
import sys
from src.ingestion import PDFParser
from src.chunking import RecursiveTextSplitter
from src.embeddings import LocalEmbedder

def main():
    # Setup directory for sample data
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    pdf_path = os.path.join(data_dir, "FY26_Q1_Consolidated_Financial_Statements.pdf")
        
    print("\n--- Starting Ingestion Pipeline ---\n")
    
    # 1. Parse PDF
    print(f"Parsing PDF document: {pdf_path}...")
    try:
        documents = PDFParser.parse(pdf_path)
    except FileNotFoundError:
        print(f"Error: Could not find the PDF file at '{pdf_path}'.")
        print("Please place your PDF file in the 'data/' folder and rename it, or update the script path.")
        sys.exit(1)
        
    print(f"Successfully parsed {len(documents)} pages.")
    for doc in documents:
        print(f"  -> {doc}")
        
    # 2. Chunk Text
    chunk_size = 300
    chunk_overlap = 50
    print(f"\nChunking documents with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}...")
    splitter = RecursiveTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(documents)
    print(f"Successfully generated {len(chunks)} chunks.")
    
    # 3. Generate Embeddings
    print("\nLoading local embedding model ('all-MiniLM-L6-v2')...")
    # This might take a moment on first run to download model files (~120MB)
    try:
        embedder = LocalEmbedder()
        print("Generating embeddings for chunks...")
        embeddings = embedder.embed_documents(chunks)
        print(f"Successfully generated {len(embeddings)} embeddings.")
        
        # Output some sample chunks with their embeddings metadata
        for i, (chunk, vector) in enumerate(zip(chunks[:3], embeddings[:3])):
            print(f"\n--- Chunk {i+1} (Page: {chunk.metadata['page']}, Chunk Index: {chunk.metadata['chunk_index']}) ---")
            print(f"Content: {chunk.page_content[:150]}...")
            print(f"Embedding dimensions: {len(vector)}")
            print(f"Embedding preview (first 5 dimensions): {vector[:5]}")
            print("-" * 40)
            
        if len(chunks) > 3:
            print(f"\n... and {len(chunks) - 3} more chunks embedded successfully.")
            
    except Exception as e:
        print(f"Error during embedding generation: {e}")
        print("Tip: Ensure 'sentence-transformers' package is installed via 'pip install -r requirements.txt'.")


if __name__ == "__main__":
    main()
