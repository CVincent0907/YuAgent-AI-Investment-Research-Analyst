"""MCP Tool wrappers — each function is traceable via LangSmith."""

# ── Dedicated portfolio tools (primary — LLM calls these directly) ────────────
from .google_sheets_tools import (
    get_portfolio_data,
    append_portfolio_row,
    update_portfolio_row,
    delete_portfolio_row,
    # Legacy shim kept for backward compatibility only
    update_portfolio_data,
)
from .brave_search_tools import search_brave_fresh_news

__all__ = [
    # Primary tools
    "get_portfolio_data",
    "append_portfolio_row",
    "update_portfolio_row",
    "delete_portfolio_row",
    "search_brave_fresh_news",
    # Legacy shim (do not expose to LLM)
    "update_portfolio_data",
]
