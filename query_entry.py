import os
import sys
import json
import re
import base64
from dotenv import load_dotenv

# 1. Load env before imports
load_dotenv()

from langsmith import traceable
from src.embeddings.embedder import LocalEmbedder
from src.vectordb.chroma_client import ChromaVectorStore
from src.agent.client import AgnesClient
from src.tools.retrieval_rag_web_tools import RetrievalGraph
from src.tools.chat_memory_tools import ChatMemory
from src.persistence.ltm_strategy import LongTermMemoryManager

# Import tools
from src.tools.financial_tools import get_financial_statements, get_ticker_news
from src.tools.python_interpreter_tools import execute_python_code
from src.tools.pdf_exporter.financial_pdf_exporter_tools import export_financial_findings_to_pdf
from src.tools.pdf_exporter.news_pdf_exporter_tools import export_news_report_to_pdf

def encode_image(image_path):
    """Encodes a local image file to base64 for the Vision model."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ensure_output_dirs():
    """Ensures the nested output directory structure exists to prevent UI crashes."""
    base_dir = "output_pdf"
    sub_dirs = ["financials", "news"]
    for sub in sub_dirs:
        path = os.path.join(base_dir, sub)
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"[System] Created directory: {path}")
    return base_dir

@traceable(name="Process Chat Turn", run_type="chain")
def process_chat_turn(user_input, store, embedder, agnes, memory, ltm, image_path=None):
    if not agnes:
        return "[AGNES_API_KEY not set] Unable to generate final answer."

    past_facts = ltm.get_past_context(user_input)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "retrieve_corrective_rag",
                "description": "Search local documents related to APPLE INC financials statement in 2026 Q1.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_statements",
                "description": "Get historical financials from Yahoo Finance.",
                "parameters": {
                    "type": "object",
                    "properties": {"ticker_symbol": {"type": "string"}},
                    "required": ["ticker_symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_ticker_news",
                "description": "Get qualitative news sentiment.",
                "parameters": {
                    "type": "object",
                    "properties": {"ticker_symbol": {"type": "string"}},
                    "required": ["ticker_symbol"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": "Run Python math/forecasts.",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search live web for trends/guidance.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_financials_to_pdf",
                "description": "Export professional financial table reports.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "title": {"type": "string"},
                        "explanation": {"type": "string"},
                        "tables_data": {"type": "object"}
                    },
                    "required": ["ticker", "title", "explanation", "tables_data"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "export_news_report_to_pdf",
                "description": "Export non-financial news summaries or profiles.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "title": {"type": "string"},
                        "analysis_summary": {"type": "string"},
                        "news_items": {"type": "array", "items": {"type": "object"}}
                    },
                    "required": ["subject", "title", "analysis_summary", "news_items"]
                }
            }
        }
    ]

    # Vision Integration: Multimodal Content
    user_content = [{"type": "text", "text": user_input}]
    if image_path:
        base64_image = encode_image(image_path)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    system_msg = f"""
        You are YuAgent, a Senior Financial Equity Analyst with vision capabilities, PDF export capabilities, and access to previous long-term memory.

        IDENTITY

        * Your name is YuAgent.
        * Your role is Senior Financial Equity Analyst.
        * When users ask:

        * "Who are you?"
        * "What is your name?"
        * "Introduce yourself"
        * "What can you do?"

        Respond as YuAgent.

        Example:
        User: Who are you?
        Assistant: I am YuAgent, a Senior Financial Equity Analyst specializing in equity research, financial statement analysis, valuation, investment analysis, and market research.

        * Do not introduce yourself as ChatGPT, GPT, OpenAI Assistant, or any other assistant name.
        * If asked about your underlying technology, explain that you are powered by a large language model while maintaining your identity as YuAgent.

        --- LONG-TERM MEMORY (PAST CONTEXT) ---
        {past_facts if past_facts else "No previous context found."}

        CORE RESPONSIBILITIES

        * Perform equity research and investment analysis.
        * Analyze annual reports, earnings reports, investor presentations, and financial statements.
        * Explain valuation methodologies including DCF, comparable company analysis, precedent transactions, and ratio analysis.
        * Generate professional investment memos and research reports.
        * Analyze uploaded images, charts, graphs, and tables.
        * Export structured reports suitable for PDF generation.

        WORKFLOW

        1. Prioritize local knowledge retrieval using `retrieve_corrective_rag`.
        2. Use long-term memory when relevant.
        3. If an image is provided, analyze charts, tables, and visual information.
        4. Use `execute_python_code` for calculations, statistics, financial modeling, and quantitative analysis.
        5. Use web search only when local knowledge is insufficient or when current information is required.
        6. Always provide citations for:

        * RAG retrieval results
        * Web search results
        * External data sources
        7. Clearly distinguish:

        * Facts
        * Assumptions
        * Estimates
        * Opinions

        RESPONSE QUALITY

        * Be accurate, concise, and professional.
        * Show calculations when performing financial analysis.
        * State uncertainties when information is incomplete.
        * Never fabricate financial data, citations, sources, or company information.
        * If evidence is insufficient, explicitly say so.

        OUTPUT FORMAT

        * Use structured headings.
        * Present tables when useful.
        * Include citations where appropriate.
        * Produce report-quality responses suitable for PDF export.
    """


    history = memory.formatted_history()
    messages = [{"role": "system", "content": system_msg}]
    if history:
        messages.append({"role": "user", "content": f"HISTORY: {history}"})
    messages.append({"role": "user", "content": user_content})

    gathered_context = []
    max_iterations = 8
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"[Agent Loop] Iteration {iteration}...")
        
        response = agnes.client.chat.completions.create(
            model=agnes.model_name, messages=messages, tools=tools, tool_choice="auto", temperature=0.0
        )
        message = response.choices[0].message
        messages.append(message)
        
        if not message.tool_calls:
            break
            
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            tool_id = tool_call.id
            
            print(f"[Agent Call Tool] {tool_name}")
            
            result = ""
            if tool_name == "retrieve_corrective_rag":
                source, matches, retrieved_text = RetrievalGraph(store, embedder).retrieve(tool_args.get("query"))
                result = f"Local RAG: {retrieved_text}"
                gathered_context.append(result)
            elif tool_name == "get_financial_statements":
                result = get_financial_statements(tool_args.get("ticker_symbol"))
                gathered_context.append(f"Financials: {result}")
            elif tool_name == "get_ticker_news":
                result = get_ticker_news(tool_args.get("ticker_symbol"))
                gathered_context.append(f"News: {result}")
            elif tool_name == "execute_python_code":
                result = execute_python_code(tool_args.get("code"))
            elif tool_name == "search_web":
                docs = RetrievalGraph(store, embedder).selector.search_web(tool_args.get("query"))
                result = "\n".join([d.page_content for d in docs])
                gathered_context.append(f"Web: {result}")
            elif tool_name == "export_financials_to_pdf":
                # Ensure the tool saves to 'output_pdf/financials/'
                result = export_financial_findings_to_pdf(**tool_args)
            elif tool_name == "export_news_report_to_pdf":
                # Ensure the tool saves to 'output_pdf/news/'
                result = export_news_report_to_pdf(**tool_args)
            
            messages.append({"role": "tool", "tool_call_id": tool_id, "name": tool_name, "content": result})

    candidate_answer = messages[-1].content if messages[-1].role == "assistant" else str(messages[-1])

    # Gatekeeper
    gatekeeper_system_msg = "You are a quality control auditor. Output 'YES' or 'NO - [reason]'."
    gatekeeper_response = agnes.client.chat.completions.create(
        model=agnes.model_name,
        messages=[{"role": "system", "content": gatekeeper_system_msg}, 
                  {"role": "user", "content": f"Query: {user_input}\nAnswer: {candidate_answer}"}],
        temperature=0.0,
    )
    gatekeeper_output = gatekeeper_response.choices[0].message.content.strip()
    print(f"[Gatekeeper Decision: {gatekeeper_output}]")

    if gatekeeper_output.upper().startswith("YES"):
        ltm.save_chat_turn(user_input, candidate_answer, True)
        return candidate_answer
    else:
        ltm.save_chat_turn(user_input, candidate_answer, False)
        return f"[Audit Note: {gatekeeper_output}]\n\n{candidate_answer}"

def start_gradio_ui():
    """Launches the Gradio Web interface with directory safety."""
    import gradio as gr
    
    # 1. Tidy up and Ensure directories exist
    root_pdf_dir = ensure_output_dirs()
    
    store = ChromaVectorStore(persist_dir=os.getenv("CHROMA_DIR"), collection_name="financial_rag")
    embedder = LocalEmbedder()
    agnes = AgnesClient()
    memory = ChatMemory()
    ltm = LongTermMemoryManager()

    def predict(message, history):
        user_text = message["text"]
        image_path = None
        for f in message["files"]:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_path = f
                break
        
        response = process_chat_turn(user_text, store, embedder, agnes, memory, ltm, image_path=image_path)
        
        memory.add_message("user", user_text)
        memory.add_message("assistant", response)
        return response

    with gr.Blocks(theme=gr.themes.Soft(), title="Analyst Agent") as demo:
        gr.Markdown("# 📈 Financial Analyst AI Dashboard")
        
        with gr.Row():
            with gr.Column(scale=4):
                gr.ChatInterface(fn=predict, multimodal=True)
            with gr.Column(scale=1):
                gr.Markdown("### 📂 Exported Files")
                # Points to the main folder containing /financials and /news
                file_exp = gr.FileExplorer(root_dir=root_pdf_dir, label="All PDF Reports")
                refresh_btn = gr.Button("🔄 Refresh Explorer")
                refresh_btn.click(lambda: None, None, file_exp)

    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)

def chat_loop():
    """CLI chat loop."""
    ensure_output_dirs()
    store = ChromaVectorStore(persist_dir=os.getenv("CHROMA_DIR"), collection_name="financial_rag")
    embedder = LocalEmbedder()
    agnes = AgnesClient()
    memory = ChatMemory()
    ltm = LongTermMemoryManager()

    print("CLI Mode. Run with --ui for Web Dashboard.\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input: continue
            answer = process_chat_turn(user_input, store, embedder, agnes, memory, ltm)
            print(f"\nAssistant: {answer}\n")
            memory.add_message("user", user_input)
            memory.add_message("assistant", answer)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        start_gradio_ui()
    else:
        chat_loop()