import asyncio
import json
import os
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from typing import Any, Dict

# Server configuration class
class ServerConfig:
    def __init__(self, command: str, args: list[str]):
        self.command = command
        self.args = args
        self.env = os.environ.copy()
        self.cwd = os.getcwd()
        # Add missing attributes expected by MCP client
        self.encoding = "utf-8"
        self.encoding_error_handler = "strict"
        self.stderr = None  # Let subprocess handle stderr normally
        self.capabilities = None

async def example_client_usage():
    """Example client usage demonstrating basic MCP operations"""
    
    print("=== MCP Client Usage Example ===\n")
    
    async with stdio_client("python", ["multiagent_mcp_server.py"]) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize session
            await session.initialize()
            print("✅ Session initialized")
            
            # List available tools
            tools = await session.list_tools()
            print(f"📋 Available tools: {[tool.name for tool in tools.tools]}")
            
            # List available resources
            resources = await session.list_resources()
            print(f"📚 Available resources: {[res.name for res in resources.resources]}")
            
            # Example 1: Process a learning request
            print("\n--- Example 1: Process Learning Request ---")
            result = await session.call_tool(
                "process_message",
                {
                    "user_input": "I want to learn about photosynthesis",
                    "user_id": "demo_user",
                    "category": "biology"
                }
            )
            response_data = json.loads(result.content[0].text)
            print(f"Agent response: {response_data['response'][:100]}...")
            
            # Example 2: Create a specific task
            print("\n--- Example 2: Create Task ---")
            task_result = await session.call_tool(
                "create_task",
                {
                    "title": "Study cell structure diagram",
                    "user_id": "demo_user",
                    "description": "Review and memorize parts of plant and animal cells",
                    "category": "biology",
                    "priority": "high"
                }
            )
            task_data = json.loads(task_result.content[0].text)
            print(f"Created task: {task_data['created_task']['title']}")
            
            # Example 3: Get tasks
            print("\n--- Example 3: Get User Tasks ---")
            tasks_result = await session.call_tool(
                "get_tasks",
                {
                    "user_id": "demo_user",
                    "category": "biology"
                }
            )
            tasks = json.loads(tasks_result.content[0].text)
            print(f"Found {len(tasks)} tasks for user")
            
            # Example 4: Read agent capabilities
            print("\n--- Example 4: Read Agent Capabilities ---")
            capabilities = await session.read_resource("agent_capabilities")
            cap_data = json.loads(capabilities.contents[0].text)
            print(f"Server supports {len(cap_data['supported_intents'])} intent types")
            
            print("\n✅ Example usage completed successfully!")


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
        },
        {
            "name": "Create Explicit Task",
            "tool": "create_task",
            "params": {
                "title": "Complete physics problem set #3",
                "user_id": "test_user",
                "description": "Work through momentum and energy problems",
                "category": "physics",
                "priority": "high"
            }
        },
        {
            "name": "Education Query Processing",
            "tool": "process_message",
            "params": {
                "user_input": "What are the laws of thermodynamics?",
                "user_id": "test_user",
                "category": "physics"
            }
        }
    ]
    
    print("=== MCP Server Test Suite ===\n")
        
    # Get the absolute path of the current file
    server_file_path = os.path.abspath("multiagent_mcp_server.py")
    
    # Create an instance of the ServerConfig class.
    # This provides the 'command' and 'args' as attributes.
    server_config = ServerConfig(
        command=sys.executable,
        args=[server_file_path, "--run-server"]
    )

    print(f"🔗 Connecting to MCP server...")
    print(f"   Command: {server_config.command}")
    print(f"   Args: {server_config.args}")

    # Connect to server and run tests
    try:
        async with stdio_client(server_config) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Server connection established\n")
                
                success_count = 0
                
                for test_case in test_cases:
                    print(f"Testing: {test_case['name']}")
                    try:
                        result = await session.call_tool(
                            test_case['tool'],
                            test_case['params']
                        )
                        print(f"✅ Success: {test_case['name']}")
                        
                        # Parse and display relevant parts of response
                        response_text = result.content[0].text
                        if len(response_text) > 200:
                            print(f"Response preview: {response_text[:200]}...\n")
                        else:
                            print(f"Response: {response_text}\n")
                        
                        success_count += 1
                        
                    except Exception as e:
                        print(f"❌ Failed: {test_case['name']}")
                        print(f"Error: {e}\n")
                
                print(f"=== Test Results: {success_count}/{len(test_cases)} passed ===\n")
                
                # Test resources
                print("Testing resources...")
                try:
                    capabilities = await session.read_resource("agent_capabilities")
                    print("✅ Successfully read agent capabilities")
                    
                    active_agents = await session.read_resource("active_agents")
                    print("✅ Successfully read active agents")
                    
                except Exception as e:
                    print(f"❌ Resource test failed: {e}")
                    
    except Exception as e:
        print(f"❌ Failed to connect to server: {e}")
        print("Make sure the server is running: python multiagent_mcp_server.py")

# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "example":
            asyncio.run(example_client_usage())
        elif mode == "test":
            asyncio.run(test_mcp_server())
        else:
            print("Usage: python test_client.py [example|test|comprehensive|interactive]")
    else:
        # Run default test suite
        asyncio.run(test_mcp_server())
        
    print("\n=== Usage Instructions ===")
    print("1. Set up your .env file with required API keys")
    print("2. Install requirements: pip install -r requirements.txt") 
    print("3. Run server: python multiagent_mcp_server.py")
    print("4. Run tests: python test_mcp.py [mode]")
    print("   Modes: example, test")