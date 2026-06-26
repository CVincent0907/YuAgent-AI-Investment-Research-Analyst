import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from src.mcp.mcp_bridge import MCPBridge

bridge = MCPBridge()
print(asyncio.run(bridge.list_tools("google-sheets")))