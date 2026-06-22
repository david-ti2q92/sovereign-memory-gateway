# Sovereign Memory Gateway (MCP)

This repository implements the **Memory Gateway** for a Sovereign Household AI Platform, adhering to the **Model Context Protocol (MCP)**.

## Architectural Context
This server resides on **Node 2A (Data Plane)** and acts as the sole interface between agentic runtimes and the household's long-term memory (PostgreSQL/Qdrant).

### Key Features
- **Namespace Isolation (MCP-INV-03):** Strictly enforces that agents (e.g., `agent-hermes`) can only read/write to their own semantic namespaces unless explicit grants are present.
- **Thin-Gateway Design:** Follows the "Thin-Gateway" rule—no business logic, only secure protocol proxying.
- **Audit Logging:** Every tool call is prepared for asynchronous logging to the household audit trail.

## Specification Alignment
- **Parent Spec:** Sovereign Household AI Master Spec v1.0
- **Integration:** MCP Addendum A
- **Transport:** Streamable HTTP (SSE) / stdio

## License
MIT (Part of the Sovereign AI Open Framework)

## Current Status: Phase 2 Functional
- [x] **MCP Protocol Scaffold:** Basic server structure implemented.
- [x] **Namespace Isolation:** Logic enforced to prevent cross-agent data access.
- [x] **Data Plane Integration:** Successfully wired to containerized PostgreSQL (`canonical_postgres`).
- [x] **Persistence Verified:** Confirmed UUID generation and storage in the `hermes.memories` schema.

## Integration Details
- **Database:** PostgreSQL 16 (Alpine Docker)
- **Schema Isolation:** Per-agent schema (e.g., `hermes.`)
- **Connection:** Secured via internal host-to-container port mapping configured through environment variables.

## MCP Transport
- Canonical SSE endpoint: `/mcp`
- Legacy SSE alias: `/sse`
- The MCP server emits a per-session message endpoint in the SSE `endpoint` event.
- Client POSTs to the message endpoint must include the exact `session_id` query parameter from that event; otherwise the MCP SDK returns HTTP 400.