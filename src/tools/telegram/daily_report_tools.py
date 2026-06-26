from langsmith import traceable

from src.tools.telegram.telegram_bot_tools import send_telegram_message
from src.msg.telegram_portfolio_report_msg import DAILY_PORTFOLIO_PROMPT


DAILY_PORTFOLIO_PROMPT = DAILY_PORTFOLIO_PROMPT

@traceable(
    name="Telegram Tool: Run & Generate Daily Portfolio Report",
    run_type="tool",
)
def run_daily_portfolio_report(
    process_chat_turn,
    store,
    embedder,
    agnes,
    memory,
    ltm,
):
    """
    Executes the existing ReAct Financial Analyst Agent and
    sends the completed report to Telegram.
    """

    print("[Daily Report] Starting autonomous portfolio analysis...")

    report = process_chat_turn(
        user_input=DAILY_PORTFOLIO_PROMPT,
        store=store,
        embedder=embedder,
        agnes=agnes,
        memory=memory,
        ltm=ltm,
    )

    send_status = send_telegram_message(report)

    print("[Daily Report] Completed.")
    print(send_status)

    return report