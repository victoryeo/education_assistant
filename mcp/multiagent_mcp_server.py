"""
MCP Server for Multi-Agent Education Assistant

This server exposes the MultiAgentEducationAssistant capabilities through the MCP protocol,
allowing other applications to interact with the multi-agent system.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime
import os
import uuid
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    Resource,
    CallToolResult,
    ListResourcesResult,
    ListToolsResult,
    ReadResourceResult
)

# Get the absolute path of the parent directory of Django app
current_dir = os.path.dirname(os.path.abspath(__file__))
django_backend_path = os.path.join(current_dir, '..', 'django-backend/djangoapp')
sys.path.append(django_backend_path)

# Import existing MultiAgentEducationAssistant
from multi_agent_assistant import MultiAgentEducationAssistant

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAgentMCPServer:
    """MCP Server wrapper for MultiAgentEducationAssistant"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}  # Using Any since we don't have the actual class
        self.active_sessions: Dict[str, str] = {}  # session_id -> agent_key

    def _get_agent_key(self, user_id: str, category: str) -> str:
        """Generate unique agent key"""
        return f"{user_id}_{category}"
    
    async def _get_or_create_agent(self, user_id: str, category: str, role_prompt: Optional[str] = None):
        """Get existing agent or create new one"""
        agent_key = self._get_agent_key(user_id, category)
        
        if agent_key not in self.agents:
            if not role_prompt:
                role_prompt = f"You are an educational assistant specializing in {category}."
            
            try:
                self.agents[agent_key] = MultiAgentEducationAssistant(
                    role_prompt=role_prompt,
                    category=category,
                    user_id=user_id
                )
                logger.info(f"Created new agent for user {user_id}, category {category}")
            except Exception as e:
                logger.error(f"Failed to create agent: {e}")
                raise
        
        return self.agents[agent_key]

# Create server instance
server = Server("multi-agent-education-assistant")
mcp_server = MultiAgentMCPServer()

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="process_message",
            description="Process a message through the multi-agent education system",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string", "description": "The user's message/query"},
                    "user_id": {"type": "string", "description": "Unique identifier for the user"},
                    "category": {"type": "string", "default": "general", "description": "Category/subject area"},
                    "role_prompt": {"type": "string", "description": "Optional custom role prompt"}
                },
                "required": ["user_input", "user_id"]
            }
        ),
        Tool(
            name="get_tasks",
            description="Get tasks for a user in a specific category",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Unique identifier for the user"},
                    "category": {"type": "string", "default": "general", "description": "Category/subject area"},
                    "status": {"type": "string", "description": "Optional status filter"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "user_id": {"type": "string", "description": "Unique identifier for the user"},
                    "description": {"type": "string", "default": "", "description": "Task description"},
                    "category": {"type": "string", "default": "general", "description": "Category/subject area"},
                    "priority": {"type": "string", "default": "medium", "description": "Task priority"}
                },
                "required": ["title", "user_id"]
            }
        ),
        Tool(
            name="get_agent_status",
            description="Get status of all agents for a user/category",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Unique identifier for the user"},
                    "category": {"type": "string", "default": "general", "description": "Category/subject area"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="analyze_intent",
            description="Analyze user intent without full processing",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string", "description": "The user's message/query"},
                    "user_id": {"type": "string", "description": "Unique identifier for the user"},
                    "category": {"type": "string", "default": "general", "description": "Category/subject area"}
                },
                "required": ["user_input", "user_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "process_message":
            user_input = arguments["user_input"]
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            role_prompt = arguments.get("role_prompt")
            
            agent = await mcp_server._get_or_create_agent(user_id, category, role_prompt)
            
            # Mock response - replace with actual agent processing
            response, created_tasks = await agent.process_message(user_input)
            
            result = {
                "response": response,
                "created_tasks": created_tasks,
                "timestamp": datetime.now().isoformat()
            }
            
            return CallToolResult(content=[TextContent(text=json.dumps(result, indent=2))])
        
        elif name == "get_tasks":
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            status = arguments.get("status")
            
            agent = await mcp_server._get_or_create_agent(user_id, category)
            
            # Mock tasks - replace with actual agent tasks
            tasks = agent.get("tasks", [])
            
            if status:
                tasks = [t for t in tasks if t.get('status') == status]
            
            return CallToolResult(content=[TextContent(text=json.dumps(tasks, indent=2))])
        
        elif name == "create_task":
            title = arguments["title"]
            user_id = arguments["user_id"]
            description = arguments.get("description", "")
            category = arguments.get("category", "general")
            priority = arguments.get("priority", "medium")
            
            agent = await mcp_server._get_or_create_agent(user_id, category)
            
            # Create new task
            new_task = {
                "id": str(uuid.uuid4()),
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "user_id": user_id
            }
            
            # Add to agent tasks (mock)
            if "tasks" not in agent:
                agent["tasks"] = []
            agent["tasks"].append(new_task)
            
            result = {
                "message": f"Created task: {title}",
                "created_task": new_task
            }
            
            return CallToolResult(content=[TextContent(text=json.dumps(result, indent=2))])
        
        elif name == "get_agent_status":
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            
            agent = await mcp_server._get_or_create_agent(user_id, category)
            
            status = {
                "user_id": user_id,
                "category": category,
                "tasks_count": len(agent.get("tasks", [])),
                "conversation_length": len(agent.get("conversation_history", [])),
                "agent_key": mcp_server._get_agent_key(user_id, category),
                "timestamp": datetime.now().isoformat()
            }
            
            return CallToolResult(content=[TextContent(text=json.dumps(status, indent=2))])
        
        elif name == "analyze_intent":
            user_input = arguments["user_input"]
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            
            # Intent analysis logic
            user_input_lower = user_input.lower()
            
            if any(keyword in user_input_lower for keyword in ["create", "add", "new", "todo"]):
                intent = "create"
            elif any(keyword in user_input_lower for keyword in ["update", "modify", "change", "edit"]):
                intent = "update"
            elif any(keyword in user_input_lower for keyword in ["complete", "done", "finished", "mark"]):
                intent = "complete"
            elif any(keyword in user_input_lower for keyword in ["summary", "list", "show", "overview"]):
                intent = "summary"
            elif any(keyword in user_input_lower for keyword in ["schedule", "deadline", "priority", "when"]):
                intent = "schedule"
            elif any(keyword in user_input_lower for keyword in ["learn", "study", "education", "course"]):
                intent = "education"
            else:
                intent = "query"
            
            result = {
                "intent": intent,
                "user_input": user_input,
                "user_id": user_id,
                "category": category,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            return CallToolResult(content=[TextContent(text=json.dumps(result, indent=2))])
        
        else:
            return CallToolResult(
                content=[TextContent(text=f"Unknown tool: {name}")],
                isError=True
            )
            
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[TextContent(text=f"Error: {str(e)}")],
            isError=True
        )

@server.list_resources()
async def list_resources() -> ListResourcesResult:
    """List available resources"""
    return ListResourcesResult(
        resources=[
            Resource(
                uri="tasks/{user_id}/{category}",
                name="User Tasks",
                description="Get all tasks for a specific user and category",
                mimeType="application/json"
            ),
            Resource(
                uri="conversation_history/{user_id}/{category}",
                name="Conversation History", 
                description="Get conversation history for a specific user and category",
                mimeType="application/json"
            ),
            Resource(
                uri="agent_capabilities",
                name="Agent Capabilities",
                description="Information about multi-agent system capabilities",
                mimeType="application/json"
            )
        ]
    )

@server.read_resource()
async def read_resource(uri: str) -> ReadResourceResult:
    """Read a specific resource"""
    try:
        if uri == "agent_capabilities":
            capabilities = {
                "agents": {
                    "task_manager": "Manages task creation, updates, and tracking",
                    "education_specialist": "Provides educational content and learning guidance",
                    "scheduler": "Handles scheduling and deadline management", 
                    "coordinator": "Coordinates responses between agents"
                },
                "supported_intents": [
                    "create", "update", "complete", "summary",
                    "schedule", "education", "query"
                ],
                "supported_categories": [
                    "general", "math", "science", "history",
                    "literature", "programming", "languages"
                ],
                "features": [
                    "Multi-agent collaboration",
                    "Task management", 
                    "Educational assistance",
                    "Scheduling support",
                    "Intent analysis",
                    "Conversation history"
                ]
            }
            
            return ReadResourceResult(
                contents=[TextContent(text=json.dumps(capabilities, indent=2))]
            )
        
        elif uri.startswith("tasks/"):
            # Parse URI: tasks/{user_id}/{category}
            parts = uri.split("/")
            if len(parts) >= 3:
                user_id = parts[1]
                category = parts[2] if len(parts) > 2 else "general"
                
                agent = await mcp_server._get_or_create_agent(user_id, category)
                tasks = agent.get("tasks", [])
                
                return ReadResourceResult(
                    contents=[TextContent(text=json.dumps(tasks, indent=2))]
                )
        
        elif uri.startswith("conversation_history/"):
            # Parse URI: conversation_history/{user_id}/{category}
            parts = uri.split("/")
            if len(parts) >= 3:
                user_id = parts[1]
                category = parts[2] if len(parts) > 2 else "general"
                
                agent = await mcp_server._get_or_create_agent(user_id, category)
                history = agent.get("conversation_history", [])
                
                return ReadResourceResult(
                    contents=[TextContent(text=json.dumps(history, indent=2))]
                )
        
        return ReadResourceResult(
            contents=[TextContent(text=f"Resource not found: {uri}")],
            isError=True
        )
        
    except Exception as e:
        logger.error(f"Error reading resource {uri}: {e}")
        return ReadResourceResult(
            contents=[TextContent(text=f"Error: {str(e)}")],
            isError=True
        )

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Multi-Agent Education Assistant MCP Server...")
    
    async with stdio_server() as streams:
        await server.run(*streams)

if __name__ == "__main__":
    asyncio.run(main())