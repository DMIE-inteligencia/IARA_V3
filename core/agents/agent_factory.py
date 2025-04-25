from typing import Dict, Optional, Type

from schema import AgentType
from core.agents.base_agent import BaseAgent
from core.agents.orchestrator_agent import OrchestratorAgent
from core.agents.llm_agent import LLMAgent
from core.agents.document_processing_agent import DocumentProcessingAgent
from core.agents.information_retrieval_agent import InformationRetrievalAgent
from core.agents.dialogue_agent import DialogueAgent
from core.agents.security_agent import SecurityAgent
from infrastructure.messaging.message_broker import MessageBroker


class AgentFactory:
    """Factory class for creating and managing agents"""
    
    def __init__(self):
        """Initialize the agent factory"""
        self.message_broker = MessageBroker()
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.agent_classes = {
            AgentType.ORCHESTRATOR: OrchestratorAgent,
            AgentType.LLM: LLMAgent,
            AgentType.DOCUMENT_PROCESSING: DocumentProcessingAgent,
            AgentType.INFORMATION_RETRIEVAL: InformationRetrievalAgent,
            AgentType.DIALOGUE: DialogueAgent,
            AgentType.SECURITY: SecurityAgent
        }
    
    def create_agent(self, agent_type: AgentType, **kwargs) -> BaseAgent:
        """Create a new agent of the specified type"""
        if agent_type not in self.agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Get the appropriate agent class
        agent_class = self.agent_classes[agent_type]
        
        # Create the agent instance
        agent = agent_class(
            agent_type=agent_type,
            message_broker=self.message_broker,
            **kwargs
        )
        
        # Store the agent
        self.agents[agent_type] = agent
        
        return agent
    
    def get_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Get an existing agent by type"""
        return self.agents.get(agent_type)
    
    def create_all_agents(self):
        """Create all agents in the correct order"""
        # Create the orchestrator first
        if AgentType.ORCHESTRATOR not in self.agents:
            self.create_agent(AgentType.ORCHESTRATOR)
        
        # Create the security agent next
        if AgentType.SECURITY not in self.agents:
            self.create_agent(AgentType.SECURITY)
        
        # Create the LLM agent
        if AgentType.LLM not in self.agents:
            self.create_agent(AgentType.LLM)
        
        # Create remaining agents
        for agent_type in self.agent_classes:
            if agent_type not in self.agents:
                self.create_agent(agent_type)
        
        # Register all agents with the orchestrator
        orchestrator = self.get_agent(AgentType.ORCHESTRATOR)
        if orchestrator:
            for agent_type, agent in self.agents.items():
                if agent_type != AgentType.ORCHESTRATOR:
                    orchestrator.register_agent(agent)
