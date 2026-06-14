import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def run_test():
    # Connect to your new Gateway
    async with sse_client("http://localhost:8091/sse") as (read, write):
        async with ClientSession(read, write) as session:
            # 1. Initialize the connection
            await session.initialize()
            
            # 2. List tools to prove discovery is working
            tools = await session.list_tools()
            print(f"Found Tools: {[t.name for t in tools.tools]}")

            # 3. Call memory_write (The actual test)
            print("Sending memory write request...")
            result = await session.call_tool("memory_write", arguments={
                "agent_id": "agent-hermes",
                "namespace": "hermes",
                "content": "The sovereign energy budget for July is 200 dollars.",
                "correlation_id": "00000000-0000-0000-0000-000000000000"
            })
            print(f"Result from Gateway: {result.content[0].text}")

if __name__ == "__main__":
    asyncio.run(run_test())