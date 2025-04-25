import logging
import threading
from typing import Dict, List, Set, Any, Callable, Optional
from queue import Queue, Empty

from schema import AgentType, Message, MessageType


class MessageBroker:
    """
    Central message broker for inter-agent communication.
    """
    
    def __init__(self):
        """Initialize the message broker"""
        self.logger = logging.getLogger("message_broker")
        
        # Subscriber queues for each agent type
        self.subscribers: Dict[AgentType, List[Callable[[Message], None]]] = {}
        
        # Response handlers keyed by correlation_id
        self.response_handlers: Dict[str, Callable[[Message], None]] = {}
        
        # Lock for thread safety
        self.lock = threading.Lock()
    
    def subscribe(self, agent_type: AgentType, callback: Callable[[Message], None]):
        """Subscribe to messages for a specific agent type"""
        with self.lock:
            if agent_type not in self.subscribers:
                self.subscribers[agent_type] = []
            
            self.subscribers[agent_type].append(callback)
            self.logger.debug(f"Agent {agent_type} subscribed to messages")
    
    def unsubscribe(self, agent_type: AgentType, callback: Optional[Callable[[Message], None]] = None):
        """Unsubscribe from messages for a specific agent type"""
        with self.lock:
            if agent_type not in self.subscribers:
                return
            
            if callback:
                # Remove specific callback
                self.subscribers[agent_type] = [
                    cb for cb in self.subscribers[agent_type] if cb != callback
                ]
            else:
                # Remove all callbacks for this agent type
                self.subscribers[agent_type] = []
            
            self.logger.debug(f"Agent {agent_type} unsubscribed from messages")
    
    def publish(self, message: Message):
        """Publish a message to its intended recipient"""
        # Check if this is a response to a previous message
        if message.message_type == MessageType.RESPONSE or message.message_type == MessageType.ERROR:
            if message.correlation_id:
                with self.lock:
                    handler = self.response_handlers.get(message.correlation_id)
                    if handler:
                        handler(message)
                        return
        
        # Deliver to subscribers
        with self.lock:
            subscribers = self.subscribers.get(message.receiver, [])
        
        if not subscribers:
            self.logger.warning(f"No subscribers for agent {message.receiver}")
            return
        
        # Deliver message to all subscribers
        for callback in subscribers:
            try:
                callback(message)
            except Exception as e:
                self.logger.error(f"Error delivering message to subscriber: {str(e)}")
    
    def register_response_handler(self, correlation_id: str, handler: Callable[[Message], None]):
        """Register a handler for a response to a specific message"""
        with self.lock:
            self.response_handlers[correlation_id] = handler
    
    def unregister_response_handler(self, correlation_id: str):
        """Unregister a response handler"""
        with self.lock:
            if correlation_id in self.response_handlers:
                del self.response_handlers[correlation_id]
