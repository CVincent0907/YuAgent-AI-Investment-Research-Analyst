import os
import re
from mem0 import Memory
from langsmith import traceable

class LongTermMemoryManager:
    def __init__(self):
        # Configuration to make Mem0 use Agnes AI for reasoning but LOCAL models for memory storage
        agnes_base = os.getenv("AGNES_BASE_URL")
        if "/chat/completions" in agnes_base:
            agnes_base = agnes_base.replace("/chat/completions", "")

        config = {
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "financial_agent_memory",
                    "path": os.getenv("MEM0_DIR")  # Directory named as you requested
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": os.getenv("AGNES_MODEL", "agnes-2.0-flash"),
                    "api_key": os.getenv("AGNES_API_KEY"),
                    "openai_base_url": agnes_base,
                    "temperature": 0
                }
            },
            # --- USE LOCAL SENTENCE TRANSFORMERS ---
            "embedder": {
                "provider": "huggingface",
                "config": {
                    "model": "sentence-transformers/all-MiniLM-L6-v2",
                }
            }
        }
        self.memory = Memory.from_config(config)
        self.user_id = "analyst_001"

    @traceable(name="Long Term Memory: Getting Previous Important Snippets")
    def get_past_context(self, user_input: str):
        """Finds relevant past facts based on the current query."""
        try:
            # Use filters for the user_id
            results = self.memory.search(user_input, filters={"user_id": self.user_id})
            
            if not results:
                return ""
            
            # Mem0 can return a dict with a 'results' key or a raw list
            data = results.get('results', results) if isinstance(results, dict) else results

            memory_strings = []
            for m in data:
                # 1. Try to get 'memory' (Standard for newer Mem0)
                # 2. Try to get 'text' (Standard for older Mem0)
                # 3. Try to get 'content' (Fallback)
                if isinstance(m, dict):
                    content = m.get('memory') or m.get('text') or m.get('content')
                    if content:
                        memory_strings.append(content)
                elif hasattr(m, 'memory'):
                    memory_strings.append(m.memory)
                elif hasattr(m, 'text'):
                    memory_strings.append(m.text)

            # Join the unique memories found
            return "\n".join([f"- {msg}" for msg in list(set(memory_strings))])
        except Exception as e:
            print(f"[LTM Error] Search failed: {e}")
            return ""
            
    @traceable(name="Long Term Memory: Consolidating New Facts")
    def save_chat_turn(self, user_input: str, assistant_output: str, confidence_flag: bool):
        """Sends the turn to Agnes AI to extract new facts for long-term storage."""
        try:
            # We save the interaction; Mem0 uses Agnes to distill it into facts
            # and then uses the local embedder to save it to .ltm_chroma
            if confidence_flag:
                full_data = f"User asked: {user_input} | Assistant replied: {assistant_output}"
            else:
                full_data = f"User asked: {user_input} | Assistant did not manage to reply confidently but providing references for user question: {assistant_output}"
            self.memory.add(full_data, user_id=self.user_id)
        except Exception as e:
            print(f"[LTM Error] Save failed: {e}")