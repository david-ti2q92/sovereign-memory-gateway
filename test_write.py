import asyncio
import json
import uuid
from main import handle_call_tool

async def test():
    print("🚀 Simulating memory_write tool call...")
    
    # Mocking the arguments an agent would send
    arguments = {
        "agent_id": "agent-hermes",
        "namespace": "hermes/",
        "content": "The Sovereign Platform Phase 2 is now live with functional database wiring.",
        "correlation_id": str(uuid.uuid4()),
        "metadata": {"source": "integration_test", "priority": "high"}
    }
    
    # Call the actual tool logic
    result = await handle_call_tool("memory_write", arguments)
    print(f"📡 Response: {result[0].text}")

if __name__ == "__main__":
    asyncio.run(test())
