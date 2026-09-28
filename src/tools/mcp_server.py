import asyncio
import sys
from pathlib import Path

# Add project root to sys.path to support direct script execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mcp.server.fastmcp import FastMCP
from src.tools.ticket_tools import (
    get_user_ticket_history,
    query_knowledge_base,
    update_ticket_status,
)

# Initialize FastMCP Server
mcp = FastMCP("Enterprise-Helpdesk-MCP")


@mcp.tool()
def search_it_knowledge_base(query: str) -> str:
    """Search internal IT SOPs, compliance rules, and resolution procedures (backed by P1 RAG)."""
    return query_knowledge_base(query)


@mcp.tool()
def modify_ticket_priority(ticket_id: str, new_priority: str, note: str) -> str:
    """Update a ticket's priority level in the helpdesk database with an audit note."""
    result = update_ticket_status(ticket_id, new_priority, note)
    return str(result)


@mcp.tool()
def lookup_user_history(user_id: str) -> str:
    """Retrieve previous ticket history and recurring issues for a specific user ID."""
    history = get_user_ticket_history(user_id)
    return "; ".join(history)


if __name__ == "__main__":
    print("[MCP Server] Starting Enterprise-Helpdesk-MCP server over stdio...")
    mcp.run()
