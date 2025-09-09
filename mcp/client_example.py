# Example client usage with mcp library
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def example_client_usage():
    """Example of how to interact with the MCP server"""
    
    # Connect to the MCP server
    async with stdio_client("python", ["multiagent_mcp_server.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize the session
            await session.initialize()
            
            # Example 1: Process a message
            print("=== Processing Message ===")
            result = await session.call_tool(
                "process_message",
                {
                    "user_input": "Create a new task to study calculus derivatives for tomorrow",
                    "user_id": "student_123",
                    "category": "math",
                    "role_prompt": "You are a calculus tutor helping students learn derivatives."
                }
            )
            print("Response:", result.content[0].text)
            
            # Example 2: Get tasks
            print("\n=== Getting Tasks ===")
            tasks_result = await session.call_tool(
                "get_tasks",
                {
                    "user_id": "student_123",
                    "category": "math"
                }
            )
            print("Tasks:", tasks_result.content[0].text)
            
            # Example 3: Analyze intent
            print("\n=== Analyzing Intent ===")
            intent_result = await session.call_tool(
                "analyze_intent",
                {
                    "user_input": "Show me my completed assignments",
                    "user_id": "student_123",
                    "category": "math"
                }
            )
            print("Intent Analysis:", intent_result.content[0].text)
            
            # Example 4: Get resources
            print("\n=== Getting Resources ===")
            resources = await session.list_resources()
            print("Available Resources:")
            for resource in resources.resources:
                print(f"  - {resource.name}: {resource.description}")
            
            # Example 5: Read a resource
            print("\n=== Reading Agent Capabilities ===")
            capabilities = await session.read_resource("agent_capabilities")
            print("Capabilities:", capabilities.contents[0].text)
