import os
import sys
import json
from dotenv import load_dotenv
import re

# Load environment variables (API keys, base URL, etc.)
load_dotenv()

from src.ingestion import PDFParser
from src.chunking import RecursiveTextSplitter
from src.embeddings.embedder import LocalEmbedder
from src.vectordb.chroma_client import ChromaVectorStore
from src.agent.client import AgnesClient
from src.tools.retrieval_selector import RetrievalGraph
from src.tools.chat_memory import ChatMemory

# Ingestion logic has been moved to `ingest_embed.py`.
# This script focuses solely on querying the existing Chroma collection.

def query_flow(user_query: str, store: ChromaVectorStore, embedder: LocalEmbedder):
    """Perform the Agentic RAG retrieval and reasoning steps for a given query."""
    # 1. Agentic rewrite (if Agnes credentials are available)
    optimized_query = user_query
    if os.getenv("AGNES_API_KEY"):
        agnes = AgnesClient()
        optimized_query = agnes.analyze_and_rewrite_query(user_query)
        print(f"Optimized query: {optimized_query}")
    else:
        print("AGNES_API_KEY not set – using original query.")

    # 2. Retrieve context via the agentic RetrievalGraph
    graph = RetrievalGraph(store=store, embedder=embedder)
    source, matches, retrieved_text = graph.retrieve(optimized_query)
    print(f"Source selected: {source}. Retrieved {len(matches)} items.")

    # 4. Final reasoning with Agnes AI (if credentials exist)
    if os.getenv("AGNES_API_KEY"):
        agnes = AgnesClient()
        final_prompt = (
            f"User query: {optimized_query}\n\n"
            f"Relevant information retrieved from documents:\n{retrieved_text}\n\n"
            "Provide a concise, accurate answer using the above context."
        )
        response = agnes.client.chat.completions.create(
            model=agnes.model_name,
            messages=[{"role": "system", "content": "You are a financial analyst assistant."},
                      {"role": "user", "content": final_prompt}],
            temperature=0.0,
            max_tokens=500,
        )
        answer = response.choices[0].message.content.strip()
        print("\n--- Final Answer ---\n")
        print(answer)
    else:
        print("AGNES_API_KEY not set – cannot perform final reasoning step.")


def chat_loop():
    """Interactive continuous chat session with Answer Relevance Gatekeeper."""
    store = ChromaVectorStore(persist_dir=".chromadb", collection_name="financial_rag")
    embedder = LocalEmbedder()
    agnes = AgnesClient() if os.getenv("AGNES_API_KEY") else None
    memory = ChatMemory()

    print("Start chatting. Press Ctrl+C to stop and reset memory.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\n[Interrupt] Conversation reset and exiting.")
            memory.clear()
            break
        if not user_input:
            continue

        # 1. Optimize query
        optimized_query = user_input
        if agnes:
            optimized_query = agnes.analyze_and_rewrite_query(user_input)
            print(f"[Optimized] {optimized_query}")

        # 2. Retrieve context
        graph = RetrievalGraph(store=store, embedder=embedder)
        source, matches, retrieved_text = graph.retrieve(optimized_query)
        print(f"Source selected: {source}. Retrieved {len(matches)} items.")

        # 3. Build prompt and Generate Candidate Answer
        history = memory.formatted_history()
        system_msg = "You are a financial analyst assistant."
        source_label = {"vector": "local docs", "vector+web": "docs + web"}.get(source, "context")

        user_msg = (
            (f"Conversation so far:\n{history}\n\n" if history else "")
            + f"User query: {optimized_query}\n\n"
            + f"Context retrieved from {source_label}:\n{retrieved_text}\n\n"
            + "Provide a concise, accurate answer using the above context."
        )

        if agnes:
            # Generate Candidate Answer
            response = agnes.client.chat.completions.create(
                model=agnes.model_name,
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
                temperature=0.0,
                max_tokens=1000,
            )
            candidate_answer = response.choices[0].message.content.strip()

            # This gatekeep reduces flexibility of model TODO 
            # --- UPDATED STEP: BINARY GATEKEEPER ---
            gatekeeper_system_msg = (
                "You are a quality control auditor. Your ONLY task is to determine if the AI Answer "
                "correctly and safely addresses the User Query based on the provided context. "
                "If the answer is relevant, accurate, and helpful, output 'YES'. "
                "If the answer is irrelevant, avoids the question, or is based on insufficient info, output 'NO'. "
                "Output ONLY the word 'YES' or 'NO'."
            )
            gatekeeper_user_msg = (
                f"User Query: {user_input}\n"
                f"AI Answer: {candidate_answer}\n\n"
                "Decision (YES/NO):"
            )

            gatekeeper_response = agnes.client.chat.completions.create(
                model=agnes.model_name,
                messages=[{"role": "system", "content": gatekeeper_system_msg}, {"role": "user", "content": gatekeeper_user_msg}],
                temperature=0.0,
            )
            
            decision = gatekeeper_response.choices[0].message.content.strip().upper()
            print(f"[Gatekeeper Decision: {decision}]")

            # Final Output Logic
            if "YES" in decision:
                final_answer = candidate_answer
            else:
                final_answer = "I'm sorry, I cannot provide a sufficiently accurate answer based on the retrieved documents."
            
            print("\nAssistant:", final_answer, "\n")
            
            # Store conversation in memory
            memory.add_message("user", user_input)
            memory.add_message("assistant", final_answer)

        else:
            print("\nAssistant: [AGNES_API_KEY not set] Unable to generate final answer.\n")
if __name__ == "__main__":
    chat_loop()

