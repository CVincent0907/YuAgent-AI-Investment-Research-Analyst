import gradio as gr
import os
import time

def create_ui(process_fn, ltm, store, embedder, agnes):
    # This logic connects the UI to your process_chat_turn
    def predict(message, history):
        # 1. Handle message content (Text + Files)
        user_text = message["text"]
        image_path = None
        
        # Check if an image was uploaded/pasted
        for file in message["files"]:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = file
                break

        # 2. Call your existing agent logic
        # We need a fresh memory object for the UI or pass the state
        from src.tools.chat_memory_tools import ChatMemory
        memory = ChatMemory() 
        # (Optional: Rebuild memory from 'history' if you want session persistence)

        response = process_fn(user_text, store, embedder, agnes, memory, ltm, image_path=image_path)
        
        return response

    # Build the Dashboard
    with gr.Blocks(theme=gr.themes.Soft(), title="Financial Analyst Agent") as demo:
        gr.Markdown("# 📈 Investment Research Analyst Agent")
        gr.Markdown("Upload charts, ask for financial models, or generate PDF reports.")
        
        with gr.Row():
            with gr.Column(scale=4):
                chat_interface = gr.ChatInterface(
                    fn=predict,
                    multimodal=True, # Enables image pasting and uploads
                    examples=[
                        {"text": "Analyze Apple's Q1 2026 performance from local RAG."},
                        {"text": "Get the income statement for TSLA and export a PDF."}
                    ]
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### 📂 Generated Reports")
                file_list = gr.FileExplorer(root_dir="output_pdf", label="Exported PDFs")
                refresh_btn = gr.Button("Refresh Folder")
                refresh_btn.click(lambda: None, None, file_list)

    return demo