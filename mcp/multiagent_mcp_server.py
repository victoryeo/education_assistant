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

from mcp import Server, Tool, Resource
from mcp.server.models import InitializationOptions
from mcp.server.session import ServerSession
from mcp.types import (
    TextContent, 
    JSONContent,
    EmbeddedResource,
    TextResourceContents,
    JSONResourceContents,
    Tool as ToolModel,
    Resource as ResourceModel
)

# Import existing MultiAgentEducationAssistant
from multi_agent_assistant import MultiAgentEducationAssistant

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAgentMCPServer:
    """MCP Server wrapper for MultiAgentEducationAssistant"""
    
    def __init__(self):
        self.server = Server("multi-agent-education-assistant")
        self.agents: Dict[str, MultiAgentEducationAssistant] = {}
        self.active_sessions: Dict[str, str] = {}  # session_id -> agent_key
        
        # Register MCP tools and resources
        self._register_tools()
        self._register_resources()
        
    def _get_agent_key(self, user_id: str, category: str) -> str:
        """Generate unique agent key"""
        return f"{user_id}_{category}"
    
    async def _get_or_create_agent(self, user_id: str, category: str, role_prompt: Optional[str] = None) -> MultiAgentEducationAssistant:
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
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.server.tool("process_message")
        async def process_message(
            user_input: str,
            user_id: str,
            category: str = "general",
            role_prompt: Optional[str] = None
        ) -> List[TextContent]:
            """
            Process a message through the multi-agent education system
            
            Args:
                user_input: The user's message/query
                user_id: Unique identifier for the user
                category: Category/subject area (e.g., "math", "science", "general")
                role_prompt: Optional custom role prompt for the education specialist
            """
            try:
                agent = await self._get_or_create_agent(user_id, category, role_prompt)
                response, created_tasks = await agent.process_message(user_input)
                
                result = {
                    "response": response,
                    "created_tasks": created_tasks,
                    "timestamp": datetime.now().isoformat()
                }
                
                return [TextContent(text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                return [TextContent(text=f"Error: {str(e)}")]
        
        @self.server.tool("get_tasks")
        async def get_tasks(
            user_id: str,
            category: str = "general",
            status: Optional[str] = None
        ) -> List[TextContent]:
            """
            Get tasks for a user in a specific category
            
            Args:
                user_id: Unique identifier for the user
                category: Category/subject area
                status: Optional status filter (pending, completed, etc.)
            """
            try:
                agent = await self._get_or_create_agent(user_id, category)
                tasks = agent.tasks
                
                if status:
                    tasks = [t for t in tasks if t.get('status') == status]
                
                return [TextContent(text=json.dumps(tasks, indent=2))]
                
            except Exception as e:
                logger.error(f"Error getting tasks: {e}")
                return [TextContent(text=f"Error: {str(e)}")]
        
        @self.server.tool("create_task")
        async def create_task(
            title: str,
            user_id: str,
            description: str = "",
            category: str = "general",
            priority: str = "medium"
        ) -> List[TextContent]:
            """
            Create a new task
            
            Args:
                title: Task title
                user_id: Unique identifier for the user
                description: Task description
                category: Category/subject area
                priority: Task priority (low, medium, high)
            """
            try:
                agent = await self._get_or_create_agent(user_id, category)
                
                # Create task through the agent's process_message method
                create_message = f"Create a new task: {title}. Description: {description}. Priority: {priority}"
                response, created_tasks = await agent.process_message(create_message)
                
                return [TextContent(text=json.dumps({
                    "message": response,
                    "created_tasks": created_tasks
                }, indent=2))]
                
            except Exception as e:
                logger.error(f"Error creating task: {e}")
                return [TextContent(text=f"Error: {str(e)}")]
        
        @self.server.tool("get_agent_status")
        async def get_agent_status(
            user_id: str,
            category: str = "general"
        ) -> List[TextContent]:
            """
            Get status of all agents for a user/category
            
            Args:
                user_id: Unique identifier for the user
                category: Category/subject area
            """
            try:
                agent = await self._get_or_create_agent(user_id, category)
                status = agent.get_agent_status()
                
                return [TextContent(text=json.dumps(status, indent=2))]
                
            except Exception as e:
                logger.error(f"Error getting agent status: {e}")
                return [TextContent(text=f"Error: {str(e)}")]
        
        @self.server.tool("analyze_intent")
        async def analyze_intent(
            user_input: str,
            user_id: str,
            category: str = "general"
        ) -> List[TextContent]:
            """
            Analyze user intent without full processing
            
            Args:
                user_input: The user's message/query
                user_id: Unique identifier for the user
                category: Category/subject area
            """
            try:
                agent = await self._get_or_create_agent(user_id, category)
                
                # Simulate intent analysis
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
                    "analysis_timestamp": datetime.now().isoformat()
                }
                
                return [TextContent(text=json.dumps(result, indent=2))]
                
            except Exception as e:
                logger.error(f"Error analyzing intent: {e}")
                return [TextContent(text=f"Error: {str(e)}")]
    
    def _register_resources(self):
        """Register MCP resources"""
        
        @self.server.resource("tasks/{user_id}/{category}")
        async def get_user_tasks(user_id: str, category: str = "general") -> str:
            """Get all tasks for a specific user and category"""
            try:
                agent = await self._get_or_create_agent(user_id, category)
                tasks = agent.tasks
                return json.dumps(tasks, indent=2)
            except Exception as e:
                logger.error(f"Error getting user tasks: {e}")
                return json.dumps({"error": str(e)})
        
        @self.server.resource("conversation_history/{user_id}/{category}")
        async def get_conversation_history(user_id: str, category: str = "general") -> str:
            """Get conversation history for a specific user and category"""
            try:
                agent = await self._get_or_create_agent(user_id, category)
                
                # Convert conversation history to serializable format
                history = []
                for msg in agent.conversation_history:
                    if hasattr(msg, 'content'):
                        history.append({
                            "type": msg.__class__.__name__,
                            "content": msg.content,
                            "timestamp": datetime.now().isoformat()
                        })
                
                return json.dumps(history, indent=2)
            except Exception as e:
                logger.error(f"Error getting conversation history: {e}")
                return json.dumps({"error": str(e)})
        
        @self.server.resource("agent_capabilities")
        async def get_agent_capabilities() -> str:
            """Get information about agent capabilities"""
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
            return json.dumps(capabilities, indent=2)
    
    async def list_resources(self) -> List[ResourceModel]:
        """List available resources"""
        return [
            ResourceModel(
                uri="tasks/{user_id}/{category}",
                name="User Tasks",
                description="Get all tasks for a specific user and category",
                mimeType="application/json"
            ),
            ResourceModel(
                uri="conversation_history/{user_id}/{category}",
                name="Conversation History",
                description="Get conversation history for a specific user and category",
                mimeType="application/json"
            ),
            ResourceModel(
                uri="agent_capabilities",
                name="Agent Capabilities",
                description="Information about multi-agent system capabilities",
                mimeType="application/json"
            )
        ]
    
    async def list_tools(self) -> List[ToolModel]:
        """List available tools"""
        return [
            ToolModel(
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
            ToolModel(
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
            ToolModel(
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
            ToolModel(
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
            ToolModel(
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

async def main():
    """Main entry point for the MCP server"""
    # Create server instance
    mcp_server = MultiAgentMCPServer()
    
    # Setup server options
    init_options = InitializationOptions(
        server_name="multi-agent-education-assistant",
        server_version="1.0.0"
    )
    
    # Create session and run server
    async with mcp_server.server.run_stdio() as session:
        logger.info("Multi-Agent Education Assistant MCP Server started")
        await session.run()

if __name__ == "__main__":
    asyncio.run(main())