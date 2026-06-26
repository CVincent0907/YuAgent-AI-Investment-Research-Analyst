import os
import asyncio
import shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import concurrent.futures

# LangSmith tracing is applied at the MCP tool layer (src/tools/mcp/),
# not here. This module is low-level infrastructure only.
def _resolve_npx() -> str:
    """Resolve full path to npx to avoid Windows PATH issues."""
    path = shutil.which("npx")
    if not path:
        raise EnvironmentError("npx not found on PATH. Please install Node.js.")
    return path


def _build_env(required: dict, base: dict = None) -> dict:
    """
    Build a clean subprocess env dict.
    Raises ValueError for any required key that is None.
    Filters out None values from optional keys.
    """
    env = dict(base or os.environ)
    for key, val in required.items():
        if val is None:
            raise ValueError(
                f"[MCPBridge] Required environment variable '{key}' is not set. "
                f"Check your .env file."
            )
        env[key] = val
    # Remove any None values that may have crept in from os.environ expansion
    return {k: v for k, v in env.items() if v is not None}


# ── Module-level singleton so we don't spawn a new npx process per call ──────
_bridge_instance = None


def get_bridge() -> "MCPBridge":
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MCPBridge()
    return _bridge_instance

# ── MCPBridge: core session manager / server registry ────────────────────────
class MCPBridge:
    def __init__(self):
        npx = _resolve_npx()

        self.servers = {
            # ── Brave Search ─────────────────────────────────────────────────
            "brave-search": StdioServerParameters(
                command=npx,
                args=["-y", "@modelcontextprotocol/server-brave-search"],
                env=_build_env(
                    required={"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY")}
                ),
            ),

            # ── Google Sheets (mcp-gsheets) ───────────────────────────────────
            # Real tool names (verified via list_tools):
            #   READ  → sheets_get_values
            #   WRITE → sheets_append_values
            "google-sheets": StdioServerParameters(
                command=npx,
                args=["-y", "mcp-gsheets@latest"],
                env=_build_env(
                    required={
                        "GOOGLE_PROJECT_ID": os.getenv("GOOGLE_PROJECT_ID"),
                        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv(
                            "GOOGLE_APPLICATION_CREDENTIALS"
                        ),
                    }
                ),
            ),
        }

    # ── Core async method ─────────────────────────────────────────────────────

    async def call_mcp_tool(
        self, server_name: str, tool_name: str, arguments: dict
    ) -> str:
        """Connect to an MCP server via stdio and call a single tool."""
        server_params = self.servers.get(server_name)
        if not server_params:
            return f"Error: MCP server '{server_name}' is not configured."

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    return result.content[0].text if result.content else "No output."
        except Exception as e:
            return (
                f"MCP Error [{server_name} / {tool_name}]: "
                f"{type(e).__name__}: {e}"
            )

    async def list_tools(self, server_name: str):
        """Utility: list all tools exposed by a server (for debugging)."""
        server_params = self.servers.get(server_name)
        if not server_params:
            return f"Error: MCP server '{server_name}' is not configured."
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [(t.name, t.description) for t in tools.tools]


# ── Public sync helper (safe inside or outside a running event loop) ──────────

def run_mcp_tool(server_name: str, tool_name: str, arguments: dict) -> str:
    """
    Synchronous wrapper around call_mcp_tool.
    Works correctly whether or not an event loop is already running
    (e.g. inside LangSmith's @traceable or Gradio's async context).
    """
    bridge = get_bridge()
    coro = bridge.call_mcp_tool(server_name, tool_name, arguments)

    try:
        # If there's already a running loop (LangSmith, Gradio, etc.),
        # asyncio.run() would raise RuntimeError — run in a thread instead.
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        # No running loop — safe to call asyncio.run() directly.
        return asyncio.run(coro)