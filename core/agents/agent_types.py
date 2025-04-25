from enum import Enum, auto
from typing import Dict, List, Set, Any


class AgentCapability(str, Enum):
    """Enum defining capabilities that agents can provide"""
    ORCHESTRATION = "orchestration"
    TEXT_GENERATION = "text_generation"
    DOCUMENT_PROCESSING = "document_processing"
    EMBEDDING_GENERATION = "embedding_generation"
    INFORMATION_RETRIEVAL = "information_retrieval"
    DIALOGUE_MANAGEMENT = "dialogue_management"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    MONITORING = "monitoring"


class AgentCapabilityRegistry:
    """Registry mapping agent types to their capabilities"""
    
    _registry: Dict[str, Set[AgentCapability]] = {
        "orchestrator": {AgentCapability.ORCHESTRATION},
        "llm": {AgentCapability.TEXT_GENERATION},
        "document_processing": {AgentCapability.DOCUMENT_PROCESSING, AgentCapability.EMBEDDING_GENERATION},
        "information_retrieval": {AgentCapability.INFORMATION_RETRIEVAL},
        "dialogue": {AgentCapability.DIALOGUE_MANAGEMENT},
        "security": {AgentCapability.AUTHENTICATION, AgentCapability.AUTHORIZATION}
    }
    
    @classmethod
    def get_capabilities(cls, agent_type: str) -> Set[AgentCapability]:
        """Get the capabilities for a specific agent type"""
        return cls._registry.get(agent_type, set())
    
    @classmethod
    def get_agent_for_capability(cls, capability: AgentCapability) -> List[str]:
        """Get agent types that provide a specific capability"""
        return [
            agent_type for agent_type, capabilities 
            in cls._registry.items() 
            if capability in capabilities
        ]
    
    @classmethod
    def register_capabilities(cls, agent_type: str, capabilities: Set[AgentCapability]):
        """Register capabilities for an agent type"""
        cls._registry[agent_type] = capabilities
