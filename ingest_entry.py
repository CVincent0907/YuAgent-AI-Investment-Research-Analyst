import os
from dotenv import load_dotenv
from ingest_embed import ingest_and_store

# Load environment variables (if any needed for embedding/model)
load_dotenv()

# ------------------------------------------------------------------
# HARDCODE YOUR PDF PATH BELOW
# Example: PDF_PATH = os.path.join("data", "FY26_Q1_Consolidated_Financial_Statements.pdf")
# Replace the string with the absolute or relative path to your PDF file.
# ------------------------------------------------------------------

def ingest_entry():
    PDF_PATH = os.path.join("data", "FY26_Q1_Consolidated_Financial_Statements.pdf")

    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}. Please place the PDF at the specified location and retry.")
        exit(1)

    # Run ingestion and embedding. This will populate the Chroma DB.
    store = ingest_and_store(PDF_PATH)
    print("Ingestion and embedding completed. Chroma DB is ready for queries.")

if __name__ == "__main__":
    ingest_entry()