import os
from typing import List, Tuple, Dict, Any
from flashrank import Ranker, RerankRequest

# Local imports
from src.embeddings.embedder import LocalEmbedder
from src.vectordb.chroma_client import ChromaVectorStore
from src.agent.client import AgnesClient

from langgraph.graph import StateGraph, END, START
from typing_extensions import TypedDict

# Simple wrapper for web results to match Chroma's Document structure
class Document:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

class RetrievalState(TypedDict, total=False):
    """Shared state flowing through the Corrective RAG graph."""
    query: str           # Original query
    matches: list        # Current list of Document objects
    retrieved_text: str  # Context string for LLM
    max_score: float     # Highest score from the reranker
    sufficient: bool     # LLM verdict
    source: str          # "vector" or "vector+web"

class RetrievalSelector:
    """Handles Retrieval, Hybrid Search logic, and Reranking."""

    def __init__(self, store: ChromaVectorStore, embedder: LocalEmbedder):
        self.store = store
        self.embedder = embedder
        self.agnes = AgnesClient()
        # Initialize a lightweight local reranker
        try:
            self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/")
        except Exception as e:
            print(f"[Selector] Reranker init failed: {e}. Falling back to basic scoring.")
            self.ranker = None

    def hybrid_recall(self, query: str, top_k: int = 20) -> List[Document]:
        """
        Retrieves a larger set of documents using Vector search.
        In a full hybrid setup, you would merge BM25 results here as well.
        """
        query_vec = self.embedder.embed_texts([query])[0]
        # We retrieve a larger pool (20) so the Reranker has enough 'candidates' to sort
        raw_results = self.store.query(query_vec, top_k=top_k)
        return [doc for doc, score in raw_results]

    def rerank_docs(self, query: str, documents: List[Document], top_n: int) -> List[Tuple[Document, float]]:
        """Uses FlashRank to re-order documents based on cross-attention relevancy."""
        if not self.ranker or not documents:
            # Fallback if reranker is missing
            return [(doc, 0.5) for doc in documents[:top_n]]

        # Prepare for FlashRank
        passages = [
            {"id": i, "text": d.page_content, "meta": d.metadata} 
            for i, d in enumerate(documents)
        ]
        
        rerank_req = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_req)

        # Map results back to Document objects
        reranked_list = []
        for res in results[:top_n]:
            idx = res['id']
            reranked_list.append((documents[idx], res['score']))
        
        return reranked_list

    def search_web(self, query: str) -> List[Document]:
        """Perform a web search and wrap results as Document objects."""
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            
            web_docs = []
            for r in results:
                content = r.get("body", "")
                meta = {
                    "source": r.get("href", "web"),
                    "title": r.get("title", "Web Result"),
                    "type": "web"
                }
                web_docs.append(Document(page_content=content, metadata=meta))
            return web_docs
        except Exception as e:
            print(f"[Selector] Web search failed: {e}")
            return []

class RetrievalGraph:
    """Corrective Agentic RAG with Dual Reranking."""

    def __init__(self, store: ChromaVectorStore, embedder: LocalEmbedder):
        self.selector = RetrievalSelector(store, embedder)
        self.agnes = self.selector.agnes
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(RetrievalState)

        # -- Node 1: Vector Retrieval + Rerank (Top 5) --
        def vector(state: RetrievalState) -> dict:
            query = state["query"]
            print(f"[RAG] Vector Stage: Recalling candidates...")
            
            # 1. Recall 20 candidates
            candidates = self.selector.hybrid_recall(query, top_k=20)
            
            # 2. Rerank down to Top 5
            reranked = self.selector.rerank_docs(query, candidates, top_n=5)
            
            max_score = reranked[0][1] if reranked else 0.0
            context_text = "\n\n".join([f"[{d.metadata.get('source')}] {d.page_content}" for d, s in reranked])
            
            return {
                "matches": [d for d, s in reranked], # Save the Top 5
                "retrieved_text": context_text,
                "max_score": max_score,
                "source": "vector"
            }

        # -- Node 2: Evaluate (LLM Verdict) --
        def evaluate(state: RetrievalState) -> dict:
            query = state["query"]
            context = state["retrieved_text"]
            max_score = state["max_score"]

            if not context.strip():
                return {"sufficient": False}

            # FAST PATH SUGGESTION: If reranker is extremely confident, skip LLM eval
            if max_score > 0.85:
                print(f"[RAG] High Confidence ({max_score:.2f}). Skipping LLM eval.")
                return {"sufficient": True}

            # LLM Evaluation
            system_prompt = (
                "You are a grader assessing if the provided context is sufficient to answer the user's query. "
                "If the context contains the specific facts needed, respond 'sufficient'. "
                "If the context is missing info or is too vague, respond 'insufficient'. "
                "Respond with only the word 'sufficient' or 'insufficient'."
            )
            user_content = f"QUERY: {query}\n\nCONTEXT:\n{context}"

            try:
                response = self.agnes.client.chat.completions.create(
                    model=self.agnes.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.0,
                    max_tokens=5
                )
                verdict = response.choices[0].message.content.strip().lower()
                is_sufficient = "sufficient" in verdict and "insufficient" not in verdict
                print(f"[RAG] LLM Evaluation: {verdict.upper()} (Score: {max_score:.2f})")
                return {"sufficient": is_sufficient}
            except Exception as e:
                # API Fallback logic
                fallback = max_score > 0.4
                print(f"[RAG] Eval API Error. Fallback to score: {fallback}")
                return {"sufficient": fallback}

        # -- Node 3: Web Search + Final Rerank (Top 10) --
        def web(state: RetrievalState) -> dict:
            query = state["query"]
            print("[RAG] Context insufficient. Invoking Web Search Tool...")
            
            # 1. Search Web
            web_docs = self.selector.search_web(query)
            
            # 2. Combine Web Docs with the previous Top 5 from Vector
            combined_pool = state["matches"] + web_docs
            
            # 3. Final Rerank of the combined pool to get the absolute Top 10
            # This ensures web data and local data compete for the top spots
            final_reranked = self.selector.rerank_docs(query, combined_pool, top_n=10)
            
            # 4. Format final context with source attribution
            final_text_parts = []
            for d, s in final_reranked:
                src = d.metadata.get('source', 'Unknown')
                final_text_parts.append(f"SOURCE: {src}\nCONTENT: {d.page_content}")
            
            final_context = "\n\n---\n\n".join(final_text_parts)
            
            return {
                "matches": [d for d, s in final_reranked],
                "retrieved_text": final_context,
                "source": "vector+web"
            }

        # -- Define Nodes --
        graph.add_node("vector", vector)
        graph.add_node("evaluate", evaluate)
        graph.add_node("web", web)

        # -- Define Edges --
        graph.add_edge(START, "vector")
        graph.add_edge("vector", "evaluate")

        def route_decision(state: RetrievalState):
            if state["sufficient"]:
                return END
            return "web"

        graph.add_conditional_edges(
            "evaluate",
            route_decision,
            {END: END, "web": "web"}
        )
        graph.add_edge("web", END)

        return graph.compile()

    def retrieve(self, query: str) -> Tuple[str, List[Any], str]:
        """
        Runs the full Corrective RAG pipeline.
        Returns (source, list_of_docs, context_string).
        """
        init_state: RetrievalState = {"query": query}
        final_state = self.graph.invoke(init_state)
        
        return (
            final_state.get("source", "vector"),
            final_state.get("matches", []),
            final_state.get("retrieved_text", "")
        )

# Example Usage:
# graph = RetrievalGraph(store, embedder)
# source, docs, context = graph.retrieve("What were the Q3 earnings for Apple?")