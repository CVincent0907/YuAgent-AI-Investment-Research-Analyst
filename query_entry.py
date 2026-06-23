import os
import sys
import json
import re
from dotenv import load_dotenv

# 1. Load env before imports to ensure all library initializations see the env vars
load_dotenv()

from langsmith import traceable # Added for tracing

from src.ingestion import PDFParser
from src.chunking import RecursiveTextSplitter
from src.embeddings.embedder import LocalEmbedder
from src.vectordb.chroma_client import ChromaVectorStore
from src.agent.client import AgnesClient
from src.tools.retrieval_rag_web_tools import RetrievalGraph
from src.tools.chat_memory_tools import ChatMemory

# Import new tools
from src.tools.financial_tools import get_financial_statements, get_ticker_news
from src.tools.python_interpreter_tools import execute_python_code
from src.tools.pdf_exporter.financial_pdf_exporter_tools import export_financial_findings_to_pdf
from src.tools.pdf_exporter.news_pdf_exporter_tools import export_news_report_to_pdf

@traceable(name="Process Chat Turn", run_type="chain")
def process_chat_turn(user_input, store, embedder, agnes, memory):
    """
    Wraps a single interaction in a trace. 
    Allows LangSmith to group everything into one tree.
    """
    if not agnes:
        return "[AGNES_API_KEY not set] Unable to generate final answer."

    # Define tools for the Agnes AI Model
    tools = [
        {
            "type": "function",
            "function": {
                "name": "retrieve_corrective_rag",
                "description": "Search and retrieve context from local financial documents (e.g. PDFs, statements).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Semantic query for RAG database retrieval."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_statements",
                "description": "Get historical financials (Income Statement, Balance Sheet, Cash Flow) for a ticker from Yahoo Finance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker_symbol": {"type": "string", "description": "The stock ticker symbol (e.g., AAPL, TSLA)."}
                    },
                    "required": ["ticker_symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_ticker_news",
                "description": "Get recent news and articles for a stock ticker to analyze qualitative news sentiment.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker_symbol": {"type": "string", "description": "The stock ticker symbol."}
                    },
                    "required": ["ticker_symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": "Run Python code to calculate financial ratios (Margins, ROE, CAGR, Debt/EBITDA) and build forecasts. Print outputs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "The python code to execute. Standard output is captured and returned."}
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Perform a live web search to find current news, management guidance, and industry trends that are not in the local database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query to look up on the web."}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_financials_to_pdf",
                "description": "Generate a professionally styled PDF report with final explanations and tables. Use this when findings (such as forecasts or ratios) are generated and the user wants to export a PDF report that involves financial tables.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string", "description": "The stock ticker symbol (e.g. AAPL)."},
                        "title": {"type": "string", "description": "Professional report title (e.g. AAPL Revenue Forecast & Valuation Analysis)."},
                        "explanation": {"type": "string", "description": "Executive summary and analysis paragraphs explaining the findings in details."},
                        "tables_data": {
                            "type": "object",
                            "description": "A dictionary where keys are table names (strings) and values are lists of lists representing rows and cells. Example: {'CAGR & Revenue Forecast': [['Metric', '2024', '2025'], ['Revenue ($B)', '394.33', '412.50'], ['Growth Rate', 'N/A', '4.6%']]}"
                        },
                        "output_filename": {"type": "string", "description": "Optional custom filename. Defaults to '<ticker>_financial_analysis_report.pdf'."}
                    },
                    "required": ["ticker", "title", "explanation", "tables_data"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_news_report_to_pdf",
                "description": "Generate a PDF report for news articles, qualitative sentiment, or profiles of people. Use this when the user wants to export non-financial news summaries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string", "description": "The person or company name."},
                        "title": {"type": "string", "description": "Title of the news brief."},
                        "analysis_summary": {"type": "string", "description": "A narrative summary of the news findings."},
                        "news_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "source": {"type": "string"},
                                    "date": {"type": "string"},
                                    "summary": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["subject", "title", "analysis_summary", "news_items"]
                }
            }
        }
    ]

    system_msg = (
        "You are a Senior Financial Equity Analyst. Your goal is to perform a forward-looking financial analysis and valuation.\n\n"
        "Your Workflow:\n"
        "1. Data Gathering: Attempt to retrieve historical financials (Income Statement, Balance Sheet, Cash Flow) for the requested ticker. "
        "Prioritize local RAG documents using `retrieve_local_rag`; if unavailable or incomplete, use the Financial Data API via `get_financial_statements`.\n"
        "2. Contextual Search: Search specifically for 'Management Guidance,' 'Earnings Call Transcripts,' and 'Industry Tailwinds' using the specialized search tool `search_web`.\n"
        "3. Quantitative Modeling: Use the Python Interpreter tool `execute_python_code` to calculate key financial ratios (Margins, ROE, Debt/EBITDA) and build a 3-year revenue forecast based on historical CAGR and guidance.\n"
        "4. Synthesis: Combine the quantitative model with qualitative news sentiment (via `get_ticker_news`) to predict the company's future performance.\n"
        "5. Audit: Every number must be cited. If the source is a local doc, provide the filename; if it is the API/Web, provide the source. If data is missing, do not hallucinate—state that the data is unavailable for modeling."
    )

    history = memory.formatted_history()
    
    messages = [
        {"role": "system", "content": system_msg}
    ]
    if history:
        messages.append({"role": "user", "content": f"Conversation history:\n{history}"})
        messages.append({"role": "user", "content": f"New Query: {user_input}"})
    else:
        messages.append({"role": "user", "content": user_input})

    gathered_context = []

    # Agent ReAct Loop
    max_iterations = 8
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"[Agent Loop] Iteration {iteration}...")
        
        response = agnes.client.chat.completions.create(
            model=agnes.model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.0
        )
        
        message = response.choices[0].message
        messages.append(message)
        
        if not message.tool_calls:
            print("[Agent Loop] No more tool calls requested. Finalizing response.")
            break
            
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_id = tool_call.id
            
            print(f"[Agent Call Tool] {tool_name} with args: {tool_args}")
            
            result = ""
            if tool_name == "retrieve_corrective_rag":
                query = tool_args.get("query")
                graph = RetrievalGraph(store=store, embedder=embedder)
                source, matches, retrieved_text = graph.retrieve(query)
                result = f"Retrieved from local RAG (source: {source}):\n{retrieved_text}"
                gathered_context.append(result)
                
            elif tool_name == "get_financial_statements":
                ticker = tool_args.get("ticker_symbol")
                result = get_financial_statements(ticker)
                gathered_context.append(f"Yahoo Finance financials for {ticker}:\n{result}")
                
            elif tool_name == "get_ticker_news":
                ticker = tool_args.get("ticker_symbol")
                result = get_ticker_news(ticker)
                gathered_context.append(f"Yahoo Finance news for {ticker}:\n{result}")
                
            elif tool_name == "execute_python_code":
                code = tool_args.get("code")
                result = execute_python_code(code)
                print(f"[Python Exec Output]\n{result}")
                
            elif tool_name == "search_web":
                query = tool_args.get("query")
                graph = RetrievalGraph(store=store, embedder=embedder)
                docs = graph.selector.search_web(query)
                if docs:
                    result = "\n\n".join([f"SOURCE: {d.metadata.get('source')}\n{d.page_content}" for d in docs])
                else:
                    result = "No web search results."
                gathered_context.append(f"Web search for '{query}':\n{result}")
            
            elif tool_name == "export_financials_to_pdf":
                # Get all arguments from the tool call
                ticker = tool_args.get("ticker")
                title = tool_args.get("title")
                explanation = tool_args.get("explanation")
                tables_data = tool_args.get("tables_data")
                output_filename = tool_args.get("output_filename") # This is optional

                # Call the actual PDF export function
                result = export_financial_findings_to_pdf(
                    ticker=ticker,
                    title=title,
                    explanation=explanation,
                    tables_data=tables_data,
                    output_filename=output_filename
                )

            elif tool_name == "export_news_report_to_pdf":
                result = export_news_report_to_pdf(
                    subject=tool_args.get("subject"),
                    title=tool_args.get("title"),
                    analysis_summary=tool_args.get("analysis_summary"),
                    news_items=tool_args.get("news_items")
                )

            else:
                result = f"Unknown tool: {tool_name}"
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": tool_name,
                "content": result
            })

    candidate_answer = messages[-1].content if messages[-1].role == "assistant" else ""
    if not candidate_answer:
        candidate_answer = str(messages[-1])

    # --- BINARY GATEKEEPER ---
    gatekeeper_system_msg = (
        "You are a quality control auditor. Your ONLY task is to determine if the AI Answer "
        "correctly and safely addresses the User Query based on the provided context. "
        "If the answer is relevant, accurate, and helpful, output 'YES'. "
        "If the answer is irrelevant, avoids the question, or is based on insufficient info, output 'NO'. "
        "Output ONLY the word 'YES' or 'NO'."
    )
    
    context_summary = "\n\n".join(gathered_context) if gathered_context else "No external context retrieved."
    gatekeeper_user_msg = (
        f"User Query: {user_input}\n"
        f"Retrieved Context:\n{context_summary}\n\n"
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
        return candidate_answer
    else:
        return f"[Audit Note: Candidate answer did not pass validation check. Gatekeeper Decision: {decision}]\n\nHere is the generated analysis for your reference:\n\n{candidate_answer}"

def chat_loop():
    """Interactive continuous chat session."""
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

        # Process the turn through the traceable function
        answer = process_chat_turn(user_input, store, embedder, agnes, memory)
        
        print("\nAssistant:", answer, "\n")
        
        # Store in memory
        memory.add_message("user", user_input)
        memory.add_message("assistant", answer)

if __name__ == "__main__":
    chat_loop()