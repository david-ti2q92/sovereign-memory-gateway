import os
import asyncio
import json
import psycopg2
from dotenv import load_dotenv
from typing import Any
from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

# Load secrets from .env
load_dotenv()

server = Server("sovereign-memory-gateway")

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="memory_write",
            description="Persist a memory to the agent's authoritative database schema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "content": {"type": "string"},
                    "correlation_id": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["agent_id", "namespace", "content", "correlation_id"]
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    if not arguments or name != "memory_write":
        raise ValueError("Invalid tool or arguments")

    agent_id = arguments.get("agent_id")
    namespace = arguments.get("namespace").rstrip('/')
    content = arguments.get("content")
    correlation_id = arguments.get("correlation_id")
    metadata = json.dumps(arguments.get("metadata", {}))

    # Invariant Enforcement
    expected_schema = agent_id.replace("agent-", "")
    if namespace != expected_schema:
        return [types.TextContent(type="text", text=f"SEC_ERROR: Unauthorized schema {namespace}")]

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = f"INSERT INTO {namespace}.memories (content, correlation_id, metadata) VALUES (%s, %s, %s) RETURNING id;"
        cur.execute(query, (content, correlation_id, metadata))
        memory_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return [types.TextContent(type="text", text=f"SUCCESS: Memory persisted. ID: {memory_id}. Schema: {namespace}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"DATABASE_ERROR: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())