import asyncio
import json
import os
import sys
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
from typing import Any, Dict
from mcp import ClientSession, StdioServerParameters

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

async def client_pdf_generate():
    """Example client usage demonstrating basic MCP operations"""
    
    print("=== MCP Client Usage Example ===\n")
    # Get the absolute path to the server script
    server_script = os.path.abspath("multiagent_mcp_server.py")
    
    # Create server config
    server_config = ServerConfig(
        command=sys.executable,
        args=[server_script]
    )
    async with stdio_client(server_config) as (read, write):
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
            # Handle the response content
            if not result.content:
                print("Error: Empty response received from server")
                return
                
            response_text = result.content[0].text
            print(f"\n--- Raw Response ---\n{response_text}\n--- End Raw Response ---\n")
            
            # Check for validation errors in the response
            if "validation error" in response_text.lower() or "validation_error" in response_text.lower():
                print("⚠️ Validation error in response:")
                print(response_text)
                return
                
            try:
                # Try to parse as JSON
                response_data = json.loads(response_text)
                if isinstance(response_data, dict):
                    if 'response' in response_data:
                        print(f"✅ Agent response: {response_data['response'][:200]}...")
                    elif 'message' in response_data:
                        print(f"✅ Message: {response_data['message']}")
                    elif 'content' in response_data:
                        print(f"✅ Content: {response_data['content']}")
                    else:
                        print(f"✅ Response data: {json.dumps(response_data, indent=2)}")

                else:
                    print(f"✅ Response: {response_data}")
            except json.JSONDecodeError:
                print(f"📝 Raw response (non-JSON): {response_text[:500]}...")
                                
            except Exception as e:
                print(f"❌ Error reading agent capabilities: {str(e)}")
            
            print("\n✅ Example usage completed successfully!")

# Main execution
if __name__ == "__main__":
    asyncio.run(client_pdf_generate())
          
    print("\n=== Usage Instructions ===")
    print("1. Set up your .env file with required API keys")
    print("2. Install requirements: pip install -r requirements.txt") 
    print("3. Run server: python multiagent_mcp_server.py")
    print("4. Run tests: python mcp_pdf.py")