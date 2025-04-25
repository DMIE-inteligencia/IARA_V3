import threading
import uuid
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any, Callable
from queue import Queue, Empty

from schema import AgentType, Message, MessageType
from infrastructure.messaging.message_broker import MessageBroker


class BaseAgent(ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker):
        """Initialize the base agent"""
        self.agent_type = agent_type
        self.message_broker = message_broker
        self.inbox: Queue[Message] = Queue()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.response_handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger(f"agent.{agent_type}")
    
    def start(self):
        """Start the agent processing loop in a separate thread"""
        if self.running:
            return
        
        self.running = True
        self.message_broker.subscribe(self.agent_type, self.receive_message)
        self.thread = threading.Thread(target=self.process_messages, daemon=True)
        self.thread.start()
        self.logger.info(f"Agent {self.agent_type} started")
    
    def stop(self):
        """Stop the agent processing loop"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        self.message_broker.unsubscribe(self.agent_type)
        self.logger.info(f"Agent {self.agent_type} stopped")
    
    def receive_message(self, message: Message):
        """Receive a message from the message broker"""
        self.inbox.put(message)
    
    def process_messages(self):
        """Process messages from the inbox"""
        while self.running:
            try:
                # Get message with timeout to allow checking running flag
                message = self.inbox.get(timeout=0.1)
                self.logger.debug(f"Processing message: {message.id} from {message.sender}")
                
                try:
                    # Handle the message
                    self.handle_message(message)
                except Exception as e:
                    self.logger.error(f"Error handling message {message.id}: {str(e)}")
                    # Send error response if this was a command
                    if message.message_type == MessageType.COMMAND:
                        self.send_error(
                            receiver=message.sender,
                            error=f"Error processing command: {str(e)}",
                            correlation_id=message.id
                        )
                
                self.inbox.task_done()
            except Empty:
                pass
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {str(e)}")
    
    @abstractmethod
    def handle_message(self, message: Message):
        """Handle a received message - must be implemented by subclasses"""
        pass
    
    def send_message(self, message: Message) -> str:
        """Send a message to another agent"""
        self.message_broker.publish(message)
        return message.id
    
    def send_response(self, original_message: Message, content: Dict[str, Any]) -> str:
        """Send a response to a received message"""
        response = Message(
            sender=self.agent_type,
            receiver=original_message.sender,
            message_type=MessageType.RESPONSE,
            content=content,
            correlation_id=original_message.id
        )
        return self.send_message(response)
    
    def send_error(self, receiver: AgentType, error: str, correlation_id: Optional[str] = None) -> str:
        """Send an error message"""
        error_message = Message(
            sender=self.agent_type,
            receiver=receiver,
            message_type=MessageType.ERROR,
            content={"error": error},
            correlation_id=correlation_id
        )
        return self.send_message(error_message)
    
    def send_message_and_wait(self, message: Message, timeout: float = 10.0) -> Optional[Message]:
        """Send a message and wait for a response"""
        # Create event to signal when response is received
        response_event = threading.Event()
        response_container = {"response": None}
        
        # Define response handler
        def response_handler(response: Message):
            response_container["response"] = response
            response_event.set()
        
        # Register response handler
        self.message_broker.register_response_handler(message.id, response_handler)
        
        try:
            # Send the message
            self.send_message(message)
            
            # Wait for response
            if response_event.wait(timeout=timeout):
                return response_container["response"]
            else:
                self.logger.warning(f"Timeout waiting for response to message {message.id}")
                return None
        finally:
            # Clean up response handler
            self.message_broker.unregister_response_handler(message.id)
