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