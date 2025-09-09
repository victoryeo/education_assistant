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
try:
    from multi_agent_assistant import MultiAgentEducationAssistant
except ImportError:
    logger.warning("Could not import MultiAgentEducationAssistant, using mock implementation")
    MultiAgentEducationAssistant = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAgentMCPServer:
    """MCP Server wrapper for MultiAgentEducationAssistant"""
    
    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}  # agent_key -> agent_data
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
                if MultiAgentEducationAssistant:
                    # Use real implementation
                    agent_instance = MultiAgentEducationAssistant(
                        role_prompt=role_prompt,
                        category=category,
                        user_id=user_id
                    )
                    self.agents[agent_key] = {
                        "instance": agent_instance,
                        "user_id": user_id,
                        "category": category,
                        "role_prompt": role_prompt,
                        "tasks": [],
                        "conversation_history": [],
                        "created_at": datetime.now().isoformat()
                    }
                else:
                    # Use mock implementation
                    self.agents[agent_key] = {
                        "instance": None,
                        "user_id": user_id,
                        "category": category,
                        "role_prompt": role_prompt,
                        "tasks": [],
                        "conversation_history": [],
                        "created_at": datetime.now().isoformat()
                    }
                
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
            name="update_task",
            description="Update an existing task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to update"},
                    "user_id": {"type": "string", "description": "Unique identifier for the user"},
                    "category": {"type": "string", "default": "general", "description": "Category/subject area"},
                    "title": {"type": "string", "description": "New task title"},
                    "description": {"type": "string", "description": "New task description"},
                    "status": {"type": "string", "description": "New task status"},
                    "priority": {"type": "string", "description": "New task priority"}
                },
                "required": ["task_id", "user_id"]
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
            
            agent_data = await mcp_server._get_or_create_agent(user_id, category, role_prompt)
            
            # Add to conversation history
            agent_data["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "user",
                "content": user_input
            })
            
            if agent_data["instance"] and MultiAgentEducationAssistant:
                # Use real agent processing
                try:
                    response, created_tasks = await agent_data["instance"].process_message(user_input)
                    
                    # Add created tasks to agent data
                    if created_tasks:
                        agent_data["tasks"].extend(created_tasks)
                except Exception as e:
                    response = f"Agent processing error: {str(e)}"
                    created_tasks = []
            else:
                # Mock response
                response = f"Mock response for '{user_input}' in category '{category}'"
                created_tasks = []
                
                # Mock task creation based on intent
                if any(keyword in user_input.lower() for keyword in ["create", "add", "new", "todo"]):
                    mock_task = {
                        "id": str(uuid.uuid4()),
                        "title": f"Task from: {user_input[:50]}...",
                        "description": f"Auto-generated task from user input",
                        "category": category,
                        "priority": "medium",
                        "status": "pending",
                        "created_at": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                    agent_data["tasks"].append(mock_task)
                    created_tasks = [mock_task]
            
            # Add response to conversation history
            agent_data["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "assistant", 
                "content": response
            })
            
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
            
            agent_data = await mcp_server._get_or_create_agent(user_id, category)
            tasks = agent_data["tasks"]
            
            if status:
                tasks = [t for t in tasks if t.get('status') == status]
            
            return CallToolResult(content=[TextContent(text=json.dumps(tasks, indent=2))])
        
        elif name == "create_task":
            title = arguments["title"]
            user_id = arguments["user_id"]
            description = arguments.get("description", "")
            category = arguments.get("category", "general")
            priority = arguments.get("priority", "medium")
            
            agent_data = await mcp_server._get_or_create_agent(user_id, category)
            
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
            
            agent_data["tasks"].append(new_task)
            
            result = {
                "message": f"Created task: {title}",
                "created_task": new_task
            }
            
            return CallToolResult(content=[TextContent(text=json.dumps(result, indent=2))])
        
        elif name == "update_task":
            task_id = arguments["task_id"]
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            
            agent_data = await mcp_server._get_or_create_agent(user_id, category)
            
            # Find and update task
            task_found = False
            for task in agent_data["tasks"]:
                if task["id"] == task_id:
                    task_found = True
                    
                    # Update fields if provided
                    if "title" in arguments:
                        task["title"] = arguments["title"]
                    if "description" in arguments:
                        task["description"] = arguments["description"]
                    if "status" in arguments:
                        task["status"] = arguments["status"]
                    if "priority" in arguments:
                        task["priority"] = arguments["priority"]
                    
                    task["updated_at"] = datetime.now().isoformat()
                    
                    result = {
                        "message": f"Updated task: {task['title']}",
                        "updated_task": task
                    }
                    break
            
            if not task_found:
                result = {
                    "error": f"Task with ID {task_id} not found"
                }
            
            return CallToolResult(content=[TextContent(text=json.dumps(result, indent=2))])
        
        elif name == "get_agent_status":
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            
            agent_data = await mcp_server._get_or_create_agent(user_id, category)
            
            status = {
                "user_id": user_id,
                "category": category,
                "tasks_count": len(agent_data["tasks"]),
                "conversation_length": len(agent_data["conversation_history"]),
                "agent_key": mcp_server._get_agent_key(user_id, category),
                "created_at": agent_data["created_at"],
                "has_real_agent": agent_data["instance"] is not None,
                "timestamp": datetime.now().isoformat()
            }
            
            return CallToolResult(content=[TextContent(text=json.dumps(status, indent=2))])
        
        elif name == "analyze_intent":
            user_input = arguments["user_input"]
            user_id = arguments["user_id"]
            category = arguments.get("category", "general")
            
            # Intent analysis logic
            user_input_lower = user_input.lower()
            confidence = 0.8
            
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
            elif "?" in user_input:
                intent = "question"
            else:
                intent = "query"
                confidence = 0.5
            
            result = {
                "intent": intent,
                "confidence": confidence,
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
            ),
            Resource(
                uri="active_agents",
                name="Active Agents",
                description="List of all currently active agents",
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
                    "schedule", "education", "query", "question"
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
                    "Conversation history",
                    "Real-time processing"
                ],
                "server_info": {
                    "name": "multi-agent-education-assistant",
                    "version": "1.0.0",
                    "has_real_agents": MultiAgentEducationAssistant is not None
                }
            }
            
            return ReadResourceResult(
                contents=[TextContent(text=json.dumps(capabilities, indent=2))]
            )
        
        elif uri == "active_agents":
            agents_info = []
            for agent_key, agent_data in mcp_server.agents.items():
                agents_info.append({
                    "agent_key": agent_key,
                    "user_id": agent_data["user_id"],
                    "category": agent_data["category"],
                    "created_at": agent_data["created_at"],
                    "tasks_count": len(agent_data["tasks"]),
                    "conversation_length": len(agent_data["conversation_history"]),
                    "has_real_instance": agent_data["instance"] is not None
                })
            
            return ReadResourceResult(
                contents=[TextContent(text=json.dumps(agents_info, indent=2))]
            )
        
        elif uri.startswith("tasks/"):
            # Parse URI: tasks/{user_id}/{category}
            parts = uri.split("/")
            if len(parts) >= 3:
                user_id = parts[1]
                category = parts[2] if len(parts) > 2 else "general"
                
                agent_data = await mcp_server._get_or_create_agent(user_id, category)
                tasks = agent_data["tasks"]
                
                return ReadResourceResult(
                    contents=[TextContent(text=json.dumps(tasks, indent=2))]
                )
        
        elif uri.startswith("conversation_history/"):
            # Parse URI: conversation_history/{user_id}/{category}
            parts = uri.split("/")
            if len(parts) >= 3:
                user_id = parts[1]
                category = parts[2] if len(parts) > 2 else "general"
                
                agent_data = await mcp_server._get_or_create_agent(user_id, category)
                history = agent_data["conversation_history"]
                
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
    
    # MCP server expects initialization_options
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            initialization_options={}
        )

if __name__ == "__main__":
    asyncio.run(main())