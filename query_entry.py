# Current mcp tools remove the content in the entry but fail to populate it but it think it has updated it 

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
from src.msg.system_msg import AGENT_ROLE_MSG, GATEKEEPER_ROLE_MSG
from src.msg.tool_msg import TOOL_DESC_MSG

# MCP Tool imports (each function is @traceable with LangSmith)
from src.tools.mcp import (
    get_portfolio_data,
    append_portfolio_row,
    update_portfolio_row,
    delete_portfolio_row,
    search_brave_fresh_news,
    update_portfolio_data,   # legacy shim — kept as safety fallback only
)

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
    tools = TOOL_DESC_MSG

    # Vision Integration: Multimodal Content
    user_content = [{"type": "text", "text": user_input}]
    if image_path:
        base64_image = encode_image(image_path)
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })

    system_msg = f"""LONG TERM MEMORY
    {past_facts if past_facts else "No previous context found."} \n
    {AGENT_ROLE_MSG}
    """

    history = memory.formatted_history()
    messages = [{"role": "system", "content": system_msg}]
    if history:
        messages.append({"role": "user", "content": f"HISTORY: {history}"})
    messages.append({"role": "user", "content": user_content})

    gathered_context = []
    max_iterations = 15
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

            # ── MCP Tool: READ portfolio from Google Sheets ───────────────────
            elif tool_name == "get_portfolio_data":
                result = get_portfolio_data()
                gathered_context.append(f"Internal Portfolio Data: {result}")

            # ── MCP Tool: APPEND new position ────────────────────────────────
            elif tool_name == "append_portfolio_row":
                result = append_portfolio_row(**tool_args)
                gathered_context.append(f"Portfolio Append Result: {result}")

            # ── MCP Tool: UPDATE fields of an existing row ──────────────────
            elif tool_name == "update_portfolio_row":
                result = update_portfolio_row(**tool_args)
                gathered_context.append(f"Portfolio Update Result: {result}")

            # ── MCP Tool: DELETE a row from portfolio ─────────────────────
            elif tool_name == "delete_portfolio_row":
                result = delete_portfolio_row(**tool_args)
                gathered_context.append(f"Portfolio Delete Result: {result}")

            # ── Legacy fallback (shim — LLM should not call this anymore) ─────
            elif tool_name == "update_portfolio_data":
                result = update_portfolio_data(**tool_args)
                gathered_context.append(f"Portfolio Update Result (legacy): {result}")

            # ── MCP Tool: Brave Search ────────────────────────────────────────
            elif tool_name == "search_brave_fresh_news":
                result = search_brave_fresh_news(
                    query=tool_args.get("query"),
                    count=tool_args.get("count", 5),
                )
                gathered_context.append(f"Fresh Market News (Brave): {result}")

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
                result = export_financial_findings_to_pdf(**tool_args)

            elif tool_name == "export_news_report_to_pdf":
                result = export_news_report_to_pdf(**tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "name": tool_name,
                "content": str(result),
            })

    last_msg = messages[-1]
    if isinstance(last_msg, dict):
        candidate_answer = last_msg.get("content", "No final answer generated by model.")
    else:
        candidate_answer = last_msg.content or "The model performed actions but provided no summary text."

    # ── Gatekeeper ────────────────────────────────────────────────────────────
    gatekeeper_system_msg = GATEKEEPER_ROLE_MSG

    gatekeeper_response = agnes.client.chat.completions.create(
        model=agnes.model_name,
        messages=[
            {"role": "system", "content": gatekeeper_system_msg},
            {"role": "user", "content": f"Query: {user_input}\nAnswer: {candidate_answer}"}
        ],
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
            if not user_input:
                continue
            answer = process_chat_turn(user_input, store, embedder, agnes, memory, ltm)
            print(f"\nAssistant: {answer}\n")
            memory.add_message("user", user_input)
            memory.add_message("assistant", answer)
        except KeyboardInterrupt:
            print("\n[Interrupt] Conversation reset and exiting.")
            memory.clear()
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        start_gradio_ui()
    else:
        chat_loop()