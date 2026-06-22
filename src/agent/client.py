import os
from typing import Optional
from openai import OpenAI
from langsmith import traceable
from langsmith.wrappers import wrap_openai

class AgnesClient:
    """Client wrapper for Agnes AI (using OpenAI-compatible interface) for Agentic RAG tasks."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """Initializes the Agnes AI Client.
        
        Loads configuration from environment variables if not explicitly provided.
        """
        self.api_key = api_key or os.getenv("AGNES_API_KEY")
        self.base_url = base_url or os.getenv("AGNES_BASE_URL", "https://api.agnes.ai/v1")
        self.model_name = model_name or os.getenv("AGNES_MODEL", "agnes-model-name")
        
        if not self.api_key:
            raise ValueError("AGNES_API_KEY is missing. Please set it in your environment or .env file.")
            
        # Standard OpenAI client pointing to the Agnes AI base URL
        self.client = wrap_openai(OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        ))

    @traceable(name="Agnes AI Query Rewrite")
    def analyze_and_rewrite_query(self, user_query: str) -> str:
        """Analyzes and expands/rewrites a user query for optimal retrieval from the vector database.
        
        This constitutes the 'Agentic' part of the RAG pipeline.
        
        Args:
            user_query: The raw query input by the user.
            
        Returns:
            An optimized search query.
        """
        system_prompt = (
            "You are an expert financial analyst assistant. Your task is to analyze the user's question "
            "and rewrite it into an optimized search query designed to retrieve relevant paragraphs from "
            "financial statements (PDF reports) in a vector database. \n\n"
            "Guidelines:\n"
            "- Focus on financial terms, accounts, metrics, and report structure.\n"
            "- Remove conversational filler, greetings, and generic questions.\n"
            "- Add synonyms or related financial terms (e.g. if query asks about 'earnings', add 'net income', 'operating income').\n"
            "- Return ONLY the optimized query text. Do not explain your reasoning or output anything else."
        )
        
        try:
            print(f"Sending query to Agnes AI ({self.model_name}) for optimization...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User query: '{user_query}'"}
                ],
                temperature=0.0,  # Deterministic output
                max_tokens=150
            )
            
            rewritten_query = response.choices[0].message.content.strip()
            # Clean up potential surrounding quotes if returned by the LLM
            if rewritten_query.startswith('"') and rewritten_query.endswith('"'):
                rewritten_query = rewritten_query[1:-1]
            if rewritten_query.startswith("'") and rewritten_query.endswith("'"):
                rewritten_query = rewritten_query[1:-1]
                
            return rewritten_query
            
        except Exception as e:
            print(f"Warning: Failed to rewrite query using Agnes AI ({e}). Falling back to original query.")
            return user_query
