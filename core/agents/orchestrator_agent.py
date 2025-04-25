import logging
from typing import Dict, List, Optional, Any

from schema import AgentType, Message, MessageType, MessagePriority
from core.agents.base_agent import BaseAgent
from infrastructure.messaging.message_broker import MessageBroker


class OrchestratorAgent(BaseAgent):
    """
    The orchestrator agent is responsible for coordinating all other agents
    in the system and managing the flow of messages between them.
    """
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker, **kwargs):
        """Initialize the orchestrator agent"""
        super().__init__(agent_type, message_broker)
        self.registered_agents: Dict[AgentType, Dict[str, Any]] = {}
        self.logger = logging.getLogger("agent.orchestrator")
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        self.registered_agents[agent.agent_type] = {
            "agent": agent,
            "status": "active",
            "capabilities": []  # In a real implementation, we'd store agent capabilities
        }
        self.logger.info(f"Registered agent: {agent.agent_type}")
    
    def unregister_agent(self, agent_type: AgentType):
        """Unregister an agent from the orchestrator"""
        if agent_type in self.registered_agents:
            del self.registered_agents[agent_type]
            self.logger.info(f"Unregistered agent: {agent_type}")
    
    def handle_message(self, message: Message):
        """Handle messages sent to the orchestrator"""
        if message.message_type == MessageType.COMMAND:
            self._handle_command(message)
        elif message.message_type == MessageType.RESPONSE:
            # Just relay responses to the right agent
            pass
        elif message.message_type == MessageType.ERROR:
            self._handle_error(message)
        elif message.message_type == MessageType.EVENT:
            self._handle_event(message)
    
    def _handle_command(self, message: Message):
        """Handle command messages"""
        action = message.content.get("action")
        
        if action == "ping":
            # Simple ping command to check if agent is alive
            self.send_response(message, {"status": "ok", "agent": self.agent_type})
        
        elif action == "get_agent_status":
            # Return status of all agents
            agent_type = message.content.get("agent_type")
            if agent_type:
                # Return status of specific agent
                if agent_type in self.registered_agents:
                    status = self.registered_agents[agent_type]["status"]
                    self.send_response(message, {"agent": agent_type, "status": status})
                else:
                    self.send_error(message.sender, f"Agent {agent_type} not found", message.id)
            else:
                # Return status of all agents
                statuses = {
                    agent_type: info["status"]
                    for agent_type, info in self.registered_agents.items()
                }
                self.send_response(message, {"agents": statuses})
        
        elif action == "route":
            # Route a message to another agent
            target_agent = message.content.get("target_agent")
            if not target_agent:
                self.send_error(message.sender, "Missing target_agent in route command", message.id)
                return
            
            payload = message.content.get("payload")
            if not payload:
                self.send_error(message.sender, "Missing payload in route command", message.id)
                return
            
            # Create and send the routed message
            routed_message = Message(
                sender=message.sender,
                receiver=target_agent,
                message_type=MessageType.COMMAND,
                content=payload,
                correlation_id=message.id
            )
            self.send_message(routed_message)
        
        else:
            # For other commands, delegate to appropriate handler
            self._dispatch_command(message)
    
    def _dispatch_command(self, message: Message):
        """Dispatch a command to the appropriate agent based on the action"""
        action = message.content.get("action", "")
        
        # Here we would implement routing logic based on the action
        # For now, we'll use a simple mapping
        if action.startswith("process_document") or action.startswith("get_document"):
            target_agent = AgentType.DOCUMENT_PROCESSING
        elif action.startswith("retrieve_") or action.startswith("search_"):
            target_agent = AgentType.INFORMATION_RETRIEVAL
        elif action.startswith("generate_") or action.startswith("translate_"):
            target_agent = AgentType.LLM
        elif action.startswith("auth_") or action.startswith("login_"):
            target_agent = AgentType.SECURITY
        elif action.startswith("chat_") or action.startswith("process_user_message"):
            target_agent = AgentType.DIALOGUE
        else:
            # Default case - we don't know how to handle this
            self.send_error(
                message.sender,
                f"Unknown action: {action}. Don't know which agent should handle it.",
                message.id
            )
            return
        
        # Check if the target agent is registered
        if target_agent not in self.registered_agents:
            self.send_error(
                message.sender,
                f"Agent {target_agent} not available to handle action {action}",
                message.id
            )
            return
        
        # Forward the message to the target agent
        forwarded_message = Message(
            sender=self.agent_type,
            receiver=target_agent,
            message_type=MessageType.COMMAND,
            content=message.content,
            correlation_id=message.id,
            priority=message.priority
        )
        self.send_message(forwarded_message)
    
    def _handle_error(self, message: Message):
        """Handle error messages"""
        error = message.content.get("error", "Unknown error")
        self.logger.error(f"Error from {message.sender}: {error}")
        
        # If there's a correlation ID, forward the error to the original sender
        if message.correlation_id:
            # Find the original message sender
            # In a real implementation, we would maintain a message history
            pass
    
    def _handle_event(self, message: Message):
        """Handle event messages"""
        event_type = message.content.get("event_type")
        
        if event_type == "agent_status_change":
            # Update agent status
            agent_type = message.content.get("agent_type")
            status = message.content.get("status")
            
            if agent_type and status and agent_type in self.registered_agents:
                self.registered_agents[agent_type]["status"] = status
                self.logger.info(f"Agent {agent_type} status changed to {status}")
