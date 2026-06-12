import os
import asyncio
from typing import Any
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.types as types
from mcp.server.stdio import stdio_server

# --- SOVEREIGN SPECIFICATION CROSS-REFERENCE ---
# Master Spec §10.2: Memory Gateway Specifications
# Addendum A §A3.2: Tool Definitions (memory_write, memory_search)

server = Server("sovereign-memory-gateway")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools for memory management."""
    return [
        types.Tool(
            name="memory_write",
            description="Write a memory entry to the agent's declared namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["agent_id", "namespace", "content"]
            },
        ),
        types.Tool(
            name="memory_search",
            description="Semantic search within a declared namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "number", "default": 5}
                },
                "required": ["agent_id", "namespace", "query"]
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution with Namespace Enforcement (MCP-INV-03)."""
    if not arguments:
        raise ValueError("Missing arguments")

    agent_id = arguments.get("agent_id")
    namespace = arguments.get("namespace")

    # --- INVARIANT ENFORCEMENT: Namespace Isolation ---
    # Per Addendum A §A3.1: Cross-namespace writes are rejected unconditionally.
    if namespace != f"{agent_id.split('-')[-1]}/": # Simple logic: agent-hermes -> hermes/
        if namespace != f"{agent_id.replace('agent-', '')}/":
             return [types.TextContent(type="text", text=f"SEC_ERROR: Agent {agent_id} unauthorized for namespace {namespace}")]

    if name == "memory_write":
        # In production, this calls PostgreSQL/Qdrant on Node 2A
        content = arguments.get("content")
        return [types.TextContent(type="text", text=f"SUCCESS: Memory persisted to {namespace}")]

    elif name == "memory_search":
        # In production, this performs a vector search
        return [types.TextContent(type="text", text=f"SUCCESS: Retrieved top results for '{arguments.get('query')}' in {namespace}")]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sovereign-memory-gateway",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())