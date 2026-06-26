import os
import requests

from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()


@traceable(name="Telegram Tool: Send Message", run_type="tool")
def send_telegram_message(message: str):
    """
    Send a Telegram message to the configured chat.
    """

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        return "Missing TELEGRAM_BOT_TOKEN"

    if not chat_id:
        return "Missing TELEGRAM_CHAT_ID"

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return "Telegram message sent successfully."

    except Exception as e:
        return f"Telegram send failed: {e}"