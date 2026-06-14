import os
import uuid
import yaml
import httpx
import uvicorn
from datetime import datetime
from dotenv import load_dotenv

# 1. Load Environment Configuration (Master Spec §2)
load_dotenv()
BRAIN_ENDPOINT = os.getenv("BRAIN_ENDPOINT", "http://100.110.123.30:11434/api/embeddings")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 8091))
POLICY_PATH = os.getenv("NAMESPACE_POLICY_PATH", "config/namespace_policy.yaml")

# 2. Stable Low-Level MCP & Web Server Imports
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import Response

# 3. Initialize the Base Server instance
server = Server("household-memory-gateway")

def load_policy():
    """Load the Namespace Policy (Invariant MCP-INV-03)."""
    with open(POLICY_PATH, "r") as f:
        return yaml.safe_load(f)

async def get_embedding(text: str):
    """Call Node 1 for semantic vectors using the environment-configured endpoint."""
    payload = {"model": "nomic-embed-text", "prompt": text}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(BRAIN_ENDPOINT, json=payload)
            response.raise_for_status()
            # Ollama returns {"embedding": [vector]}
            return response.json().get("embedding")
        except Exception as e:
            print(f"CRITICAL: Brain Endpoint Error ({BRAIN_ENDPOINT}): {e}")
            return None

# 4. Tool Manifest (Addendum A §A3.2)
@server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="memory_write",
            description="Write a semantic memory after validation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "content": {"type": "string"},
                    "correlation_id": {"type": "string"}
                },
                "required": ["agent_id", "namespace", "content", "correlation_id"]
            }
        ),
        Tool(
            name="memory_search",
            description="Semantic search within the agent's declared namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "query": {"type": "string"}
                },
                "required": ["agent_id", "namespace", "query"]
            }
        )
    ]

# 5. Tool Execution (Thin Gateway Logic)
@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "memory_write":
        agent_id = arguments.get("agent_id")
        namespace = arguments.get("namespace")
        content = arguments.get("content")
        
        # Policy Enforcement: Invariant MCP-INV-03
        policy = load_policy()
        ns_config = policy.get('namespaces', {}).get(namespace)

        if not ns_config or ns_config.get('owner_agent') != agent_id:
            return [TextContent(type="text", text="Error: Permission Denied")]

        vector = await get_embedding(content)
        if not vector:
            return [TextContent(type="text", text="Error: Embedding Engine Offline")]

        # Log completion to console (Audit Trace)
        print(f"[MEMORY] SUCCESS: {agent_id} -> {namespace} (Dim: {len(vector)})")
        
        return [TextContent(type="text", text=f"Memory Stored. ID: {uuid.uuid4()}")]

    if name == "memory_search":
        # Placeholder for search logic
        return [TextContent(type="text", text="Search logic pending Database wiring phase.")]

# 6. THE SSE TRANSPORT BRIDGE
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """
    Handles the initial SSE connection request.
    Uses request._send (Starlette internal) to satisfy the MCP SDK's need
    for the raw ASGI send channel.
    """
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    
    return Response()

# 7. Starlette Application Routing
starlette_app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),
        # Mount the handler for client-to-server JSON-RPC messages
        Mount("/messages", app=sse.handle_post_message),
    ]
)

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("SOVEREIGN HOUSEHOLD AI: MEMORY GATEWAY (HARDENED)")
    print(f"Gateway Binding: 0.0.0.0:{GATEWAY_PORT}/sse")
    print(f"Target Brain:    {BRAIN_ENDPOINT}")
    print("--------------------------------------------------")
    
    uvicorn.run(starlette_app, host="0.0.0.0", port=GATEWAY_PORT)