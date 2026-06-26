from langsmith import traceable

from src.tools.telegram.telegram_bot_tools import send_telegram_message


DAILY_PORTFOLIO_PROMPT = """
You are acting as my autonomous investment research analyst.

Perform a complete morning investment review.

Your objectives are:

1. Retrieve my current investment portfolio.
2. Review today's important macroeconomic events.
3. Review overnight US market performance.
4. Review today's Asian and global market outlook.
5. Review breaking news affecting my portfolio holdings.
6. Identify positive and negative catalysts.
7. Evaluate company fundamentals if new financial data is available.
8. Assess portfolio risks.
9. Identify opportunities.
10. Predict today's likely market direction.
11. Recommend whether each holding should be:
   • Buy More
   • Hold
   • Reduce
   • Sell

Finally provide:

• Executive Summary
• Portfolio Health Score
• Top 5 Important News
• Top Risks
• Top Opportunities
• Recommended Actions

Use every tool available whenever necessary.
Always explain your reasoning.
"""


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