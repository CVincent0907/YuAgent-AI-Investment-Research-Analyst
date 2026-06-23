import os
from typing import List, Tuple, Dict, Any
from flashrank import Ranker, RerankRequest
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv
from langsmith import traceable

# Load environment variables (Make sure LANGCHAIN_TRACING_V2=true is in your .env)
load_dotenv() 

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
    query: str           
    matches: list        
    retrieved_text: str  
    max_score: float     
    sufficient: bool     
    source: str          

class RetrievalSelector:
    """Handles Hybrid Search (Vector + BM25), Web Search, and Reranking."""

    def __init__(self, store: ChromaVectorStore, embedder: LocalEmbedder):
        self.store = store
        self.embedder = embedder
        self.agnes = AgnesClient()
        
        # 1. Initialize Reranker
        try:
            self.ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/")
        except Exception as e:
            print(f"[Selector] Reranker init failed: {e}")
            self.ranker = None

        # 2. Initialize BM25 Index
        try:
            all_docs = self.store.collection.get()
            self.corpus_documents = []
            tokenized_corpus = []

            for i in range(len(all_docs['documents'])):
                content = all_docs['documents'][i]
                meta = all_docs['metadatas'][i]
                doc = Document(page_content=content, metadata=meta)
                self.corpus_documents.append(doc)
                tokenized_corpus.append(content.lower().split())

            self.bm25 = BM25Okapi(tokenized_corpus)
        except Exception as e:
            print(f"[Selector] BM25 init failed: {e}")
            self.bm25 = None

    @traceable(name="Node Process: Hybrid Recall (Vector + BM25)")
    def hybrid_recall(self, query: str, top_k: int = 20) -> List[Document]:
        """Combines Vector (Dense) and BM25 (Sparse) retrieval."""
        # Vector Search
        query_vec = self.embedder.embed_texts([query])[0]
        vector_results = self.store.query(query_vec, top_k=top_k)
        vector_docs = [doc for doc, score in vector_results]

        # BM25 Search
        bm25_docs = []
        if self.bm25:
            tokenized_query = query.lower().split()
            bm25_docs = self.bm25.get_top_n(tokenized_query, self.corpus_documents, n=top_k)

        # Merge and Deduplicate
        seen_content = set()
        combined_pool = []
        for doc in (vector_docs + bm25_docs):
            if doc.page_content not in seen_content:
                combined_pool.append(doc)
                seen_content.add(doc.page_content)
        
        return combined_pool

    @traceable(name="Node Process: FlashRank Reranking")
    def rerank_docs(self, query: str, documents: List[Document], top_n: int) -> List[Tuple[Document, float]]:
        """Uses FlashRank to re-order documents."""
        if not self.ranker or not documents:
            return [(doc, 0.5) for doc in documents[:top_n]]

        passages = [{"id": i, "text": d.page_content, "meta": d.metadata} for i, d in enumerate(documents)]
        rerank_req = RerankRequest(query=query, passages=passages)
        results = self.ranker.rerank(rerank_req)

        reranked_list = []
        for res in results[:top_n]:
            idx = res['id']
            reranked_list.append((documents[idx], res['score']))
        
        return reranked_list

    @traceable(name="Tool: Web Search")
    def search_web(self, query: str) -> List[Document]:
        """Perform a web search via DuckDuckGo."""
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            return [Document(page_content=r.get("body", ""), 
                             metadata={"source": r.get("href", "web"), "type": "web"}) for r in results]
        except Exception as e:
            print(f"[Selector] Web search failed: {e}")
            return []

class RetrievalGraph:
    """Corrective Agentic RAG with Hybrid Search & Dual Reranking."""

    def __init__(self, store: ChromaVectorStore, embedder: LocalEmbedder):
        self.selector = RetrievalSelector(store, embedder)
        self.agnes = self.selector.agnes
        self.graph = self._build_graph()

    @traceable(name="Node: Hybrid Retrieve")
    def _node_hybrid_retrieve(self, state: RetrievalState) -> dict:
        query = state["query"]
        candidates = self.selector.hybrid_recall(query, top_k=25)
        reranked = self.selector.rerank_docs(query, candidates, top_n=5)
        
        max_score = reranked[0][1] if reranked else 0.0
        context_text = "\n\n".join([f"[{d.metadata.get('source')}] {d.page_content}" for d, s in reranked])
        
        return {
            "matches": [d for d, s in reranked],
            "retrieved_text": context_text,
            "max_score": max_score,
            "source": "hybrid_vector"
        }

    @traceable(name="Node: Evaluate Sufficiency")
    def _node_evaluate(self, state: RetrievalState) -> dict:
        query = state["query"]
        context = state["retrieved_text"]
        max_score = state["max_score"]

        if not context.strip(): return {"sufficient": False}
        if max_score > 0.85: return {"sufficient": True}

        system_prompt = "Respond ONLY 'sufficient' or 'insufficient' based on context relevance to query."
        user_content = f"QUERY: {query}\n\nCONTEXT:\n{context}"

        try:
            response = self.agnes.client.chat.completions.create(
                model=self.agnes.model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                temperature=0.0,
                max_tokens=5
            )
            verdict = response.choices[0].message.content.strip().lower()
            return {"sufficient": "sufficient" in verdict and "insufficient" not in verdict}
        except:
            return {"sufficient": max_score > 0.4}

    @traceable(name="Node: Web Search & Rerank")
    def _node_web(self, state: RetrievalState) -> dict:
        query = state["query"]
        web_docs = self.selector.search_web(query)
        combined_pool = state["matches"] + web_docs
        final_reranked = self.selector.rerank_docs(query, combined_pool, top_n=10)
        
        final_text = "\n\n---\n\n".join([f"SOURCE: {d.metadata.get('source')}\n{d.page_content}" for d, s in final_reranked])
        
        return {
            "matches": [d for d, s in final_reranked],
            "retrieved_text": final_text,
            "source": "hybrid+web"
        }

    def _build_graph(self):
        graph = StateGraph(RetrievalState)

        # Use the class methods as nodes
        graph.add_node("hybrid_retrieve", self._node_hybrid_retrieve)
        graph.add_node("evaluate", self._node_evaluate)
        graph.add_node("web", self._node_web)

        graph.add_edge(START, "hybrid_retrieve")
        graph.add_edge("hybrid_retrieve", "evaluate")
        graph.add_conditional_edges("evaluate", lambda x: END if x["sufficient"] else "web", {END: END, "web": "web"})
        graph.add_edge("web", END)

        return graph.compile()

    @traceable(name="Tool: Corrective RAG")
    def retrieve(self, query: str) -> Tuple[str, List[Any], str]:
        """Runs the full Corrective RAG pipeline."""
        init_state: RetrievalState = {"query": query}
        final_state = self.graph.invoke(init_state)
        
        return (
            final_state.get("source", "hybrid"),
            final_state.get("matches", []),
            final_state.get("retrieved_text", "")
        )