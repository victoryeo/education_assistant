import json

async def test_mcp_server():
    """Test script for the MCP server"""
    
    test_cases = [
        {
            "name": "Create Math Task",
            "tool": "process_message",
            "params": {
                "user_input": "Create a task to practice quadratic equations",
                "user_id": "test_user",
                "category": "math"
            }
        },
        {
            "name": "Get Task List",
            "tool": "get_tasks",
            "params": {
                "user_id": "test_user",
                "category": "math"
            }
        },
        {
            "name": "Intent Analysis",
            "tool": "analyze_intent",
            "params": {
                "user_input": "I need help with my physics homework",
                "user_id": "test_user",
                "category": "physics"
            }
        },
        {
            "name": "Agent Status",
            "tool": "get_agent_status",
            "params": {
                "user_id": "test_user",
                "category": "math"
            }
        }
    ]
    
    print("=== MCP Server Test Suite ===\n")
    
    # Connect to server and run tests
    async with stdio_client("python", ["multiagent_mcp_server.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            for test_case in test_cases:
                print(f"Testing: {test_case['name']}")
                try:
                    result = await session.call_tool(
                        test_case['tool'],
                        test_case['params']
                    )
                    print(f"✅ Success: {test_case['name']}")
                    print(f"Response preview: {result.content[0].text[:100]}...\n")
                except Exception as e:
                    print(f"❌ Failed: {test_case['name']}")
                    print(f"Error: {e}\n")

# Run tests
if __name__ == "__main__":
    # Uncomment to run client example
    # asyncio.run(example_client_usage())
    
    # Uncomment to run tests
    # asyncio.run(test_mcp_server())
    
    print("Configuration and examples ready!")
    print("1. Set up your .env file with required API keys")
    print("2. Install requirements: pip install -r requirements.txt")
    print("3. Run server: python multiagent_mcp_server.py")
    print("4. Or use with Claude Desktop by updating configuration")