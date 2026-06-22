import json
import os
from typing import Any

import httpx
import uvicorn
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

load_dotenv()

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "localhost")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", 8091))
GATEWAY_AUTH_TOKEN = os.getenv("GATEWAY_AUTH_TOKEN", "")
MEMORY_BACKEND_URL = os.getenv("MEMORY_BACKEND_URL", "http://localhost:8093/mcp/tools/invoke")

server = Server("household-memory-gateway")
mcp_bridge = SseServerTransport("/messages")


def is_authorized_request(request: Request) -> bool:
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    provided_token = auth_header.split(" ", 1)[1].strip()
    return bool(GATEWAY_AUTH_TOKEN and provided_token == GATEWAY_AUTH_TOKEN)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not is_authorized_request(request):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


def auth_header() -> dict[str, str]:
    return {"Authorization": f"Bearer {GATEWAY_AUTH_TOKEN}"} if GATEWAY_AUTH_TOKEN else {}


def tool_result(payload: dict[str, Any]):
    return [TextContent(type="text", text=json.dumps(payload, sort_keys=True))]


async def proxy_tool_call(name: str, arguments: dict[str, Any]) -> Any:
    payload = {
        "tool": name,
        "arguments": arguments,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(MEMORY_BACKEND_URL, json=payload, headers=auth_header())
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


async def invoke_tool(request: Request):
    payload = await request.json()
    name = payload.get("tool", "")
    arguments = payload.get("arguments", {})

    try:
        result = await proxy_tool_call(name, arguments if isinstance(arguments, dict) else {})
        return JSONResponse(result)
    except httpx.HTTPError as exc:
        return JSONResponse(
            {"schema_version": "v1", "error": "backend_unavailable", "detail": str(exc), "tool": name},
            status_code=502,
        )


@server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="memory_write",
            description="Write a semantic memory entry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema_version": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "content": {"type": "string"},
                    "metadata": {"type": "object"},
                    "ttl_days": {"type": ["number", "null"]},
                },
                "required": ["schema_version", "agent_id", "namespace", "content", "metadata"],
            },
        ),
        Tool(
            name="memory_search",
            description="Search semantic memory entries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema_version": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "namespace": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "number"},
                    "filter": {"type": "object"},
                },
                "required": ["schema_version", "agent_id", "namespace", "query"],
            },
        ),
        Tool(
            name="memory_delete",
            description="Soft-delete a memory entry by ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema_version": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "memory_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["schema_version", "agent_id", "memory_id", "reason"],
            },
        ),
        Tool(
            name="state_read",
            description="Read canonical household state by key.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema_version": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "key": {"type": "string"},
                },
                "required": ["schema_version", "agent_id", "key"],
            },
        ),
        Tool(
            name="state_list_keys",
            description="List canonical household state keys.",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema_version": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "prefix": {"type": ["string", "null"]},
                },
                "required": ["schema_version", "agent_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    try:
        result = await proxy_tool_call(name, arguments)
    except httpx.HTTPError as exc:
        return tool_result({"schema_version": "v1", "error": "backend_unavailable", "detail": str(exc), "tool": name})

    if isinstance(result, dict):
        return tool_result(result)
    return tool_result({"schema_version": "v1", "result": result})


async def handle_sse(request: Request):
    async with mcp_bridge.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
    return Response()


async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "memory-gateway", "port": GATEWAY_PORT})


starlette_app = Starlette(
    routes=[
        Route("/health", endpoint=health, methods=["GET"]),
        Route("/mcp/tools/invoke", endpoint=invoke_tool, methods=["POST"]),
        Mount(
            "/mcp",
            app=Starlette(
                routes=[
                    Route("/", endpoint=handle_sse, methods=["GET"]),
                    Mount("/messages", app=mcp_bridge.handle_post_message),
                ],
            ),
        ),
        Mount(
            "/sse",
            app=Starlette(
                routes=[
                    Route("/", endpoint=handle_sse, methods=["GET"]),
                    Mount("/messages", app=mcp_bridge.handle_post_message),
                ],
            ),
        ),
    ],
)
starlette_app.mount("/messages", app=mcp_bridge.handle_post_message)
starlette_app.router.redirect_slashes = True
starlette_app.add_middleware(AuthMiddleware)


if __name__ == "__main__":
    uvicorn.run(starlette_app, host=GATEWAY_HOST, port=GATEWAY_PORT)
