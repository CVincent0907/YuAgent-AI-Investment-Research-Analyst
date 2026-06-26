"""
MCP Tool: Brave Search
Wraps mcp_bridge calls for fresh web/news search via the Brave Search MCP server.
Each function is marked as an MCP Tool for LangSmith traceability.
"""

from langsmith import traceable
from src.mcp.mcp_bridge import run_mcp_tool


@traceable(name="MCP Tool: Search Brave Fresh News")
def search_brave_fresh_news(query: str, count: int = 5) -> str:
    """
    MCP Tool — Fetches fresh web/news results from the Brave Search MCP server.

    Args:
        query: The search query string.
        count: Maximum number of results to return (default 5).

    Returns:
        A string containing search result snippets or an MCP error message.
    """
    return run_mcp_tool(
        "brave-search",
        "brave_web_search",
        {"query": query, "count": count},
    )
