import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from schema import (
    AgentType, Message, MessageType, ChatMessage, ChatSession,
    RetrievalResult, MessagePriority
)
from core.agents.base_agent import BaseAgent
from core.rag.prompts import RAGPromptTemplates
from core.rag.chains import RAGChain
from infrastructure.messaging.message_broker import MessageBroker


class DialogueAgent(BaseAgent):
    """
    The dialogue agent is responsible for managing conversations with users,
    processing their inputs, and coordinating with other agents to generate responses.
    """
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker, **kwargs):
        """Initialize the dialogue agent"""
        super().__init__(agent_type, message_broker)
        self.logger = logging.getLogger("agent.dialogue")
        
        # Initialize components
        self.prompt_templates = RAGPromptTemplates()
        self.rag_chain = RAGChain()
        
        # Session storage (would be replaced with a database in production)
        self.sessions: Dict[str, ChatSession] = {}
    
    def handle_message(self, message: Message):
        """Handle messages sent to the dialogue agent"""
        if message.message_type == MessageType.COMMAND:
            self._handle_command(message)
    
    def _handle_command(self, message: Message):
        """Handle command messages"""
        action = message.content.get("action")
        
        if action == "process_user_message":
            self._handle_process_user_message(message)
        elif action == "create_session":
            self._handle_create_session(message)
        elif action == "get_session":
            self._handle_get_session(message)
        elif action == "list_sessions":
            self._handle_list_sessions(message)
        elif action == "delete_session":
            self._handle_delete_session(message)
        else:
            self.send_error(
                message.sender,
                f"Unknown action: {action}",
                message.id
            )
    
    def _handle_process_user_message(self, message: Message):
        """Handle user message processing requests"""
        user_message_data = message.content.get("message", {})
        session_id = message.content.get("session_id")
        user_id = message.content.get("user_id")
        documents = message.content.get("documents", [])
        
        if not user_message_data:
            self.send_error(message.sender, "Missing message parameter", message.id)
            return
        
        if not session_id:
            self.send_error(message.sender, "Missing session_id parameter", message.id)
            return
        
        try:
            # Get or create session
            session = self.sessions.get(session_id)
            if not session:
                session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    model_id="gpt-4o",  # Default model
                    document_ids=documents
                )
                self.sessions[session_id] = session
            
            # Create user message object
            user_message = ChatMessage(**user_message_data)
            
            # Add to session history
            session.messages.append(user_message)
            session.updated_at = datetime.now()
            
            # Process message and generate response
            response_message = self._generate_response(user_message, session)
            
            # Add to session history
            session.messages.append(response_message)
            
            # Send response
            self.send_response(
                message,
                {
                    "message": response_message.dict(),
                    "session_id": session_id
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing user message: {str(e)}")
            self.send_error(
                message.sender,
                f"Error processing user message: {str(e)}",
                message.id
            )
    
    def _generate_response(self, user_message: ChatMessage, session: ChatSession) -> ChatMessage:
        """Generate a response to a user message"""
        # Get conversation history
        conversation_history = session.messages[-10:]  # Use last 10 messages for context
        
        # Extract just the document IDs from the session
        document_ids = session.document_ids
        
        if not document_ids:
            # If no documents are associated with the session, generate a simple response
            return self._generate_simple_response(user_message, conversation_history, session)
        
        # Create a message to retrieve relevant document chunks
        retrieval_message = Message(
            sender=self.agent_type,
            receiver=AgentType.INFORMATION_RETRIEVAL,
            message_type=MessageType.COMMAND,
            priority=MessagePriority.HIGH,
            content={
                "action": "retrieve",
                "query": user_message.content,
                "filters": {"document_id": document_ids},
                "num_results": 5
            }
        )
        
        # Send retrieval request and wait for response
        retrieval_response = self.send_message_and_wait(retrieval_message)
        
        if not retrieval_response or retrieval_response.message_type == MessageType.ERROR:
            # If retrieval fails, fall back to simple response
            self.logger.warning("Document retrieval failed, falling back to simple response")
            return self._generate_simple_response(user_message, conversation_history, session)
        
        # Extract retrieval results
        results = retrieval_response.content.get("results", [])
        
        if not results:
            # If no relevant chunks found, generate a response indicating this
            return ChatMessage(
                message_id=str(uuid.uuid4()),
                user_id=user_message.user_id,
                session_id=session.session_id,
                role="assistant",
                content="I don't have enough information in the documents to answer this question. Could you provide more context or ask something else about the documents?",
                timestamp=datetime.now()
            )
        
        # Create the LLM request for RAG response
        context_chunks = [result["content"] for result in results]
        citations = [
            {
                "document_id": result["document_id"],
                "chunk_id": result["chunk_id"],
                "content": result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
            }
            for result in results
        ]
        
        # Prepare the prompt with context
        prompt = self.prompt_templates.get_rag_prompt(
            query=user_message.content,
            context=context_chunks,
            chat_history=conversation_history
        )
        
        # Generate the response using the LLM
        llm_message = Message(
            sender=self.agent_type,
            receiver=AgentType.LLM,
            message_type=MessageType.COMMAND,
            priority=MessagePriority.HIGH,
            content={
                "action": "generate_text",
                "prompt": prompt,
                "model": session.model_id
            }
        )
        
        llm_response = self.send_message_and_wait(llm_message)
        
        if not llm_response or llm_response.message_type == MessageType.ERROR:
            # If LLM generation fails, return an error message
            return ChatMessage(
                message_id=str(uuid.uuid4()),
                user_id=user_message.user_id,
                session_id=session.session_id,
                role="assistant",
                content="I'm sorry, I encountered an error while processing your question. Please try again.",
                timestamp=datetime.now()
            )
        
        # Extract generated text
        generated_text = llm_response.content.get("text", "")
        
        # Create the assistant message
        return ChatMessage(
            message_id=str(uuid.uuid4()),
            user_id=user_message.user_id,
            session_id=session.session_id,
            role="assistant",
            content=generated_text,
            timestamp=datetime.now(),
            document_ids=list(set(result["document_id"] for result in results)),
            citations=citations
        )
    
    def _generate_simple_response(self, user_message: ChatMessage, conversation_history: List[ChatMessage], session: ChatSession) -> ChatMessage:
        """Generate a simple response when no documents are available"""
        # Prepare conversation context
        conversation_context = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in conversation_history
        ])
        
        # Prepare prompt
        prompt = self.prompt_templates.get_conversation_prompt(
            query=user_message.content,
            conversation_history=conversation_context
        )
        
        # Generate response using LLM
        llm_message = Message(
            sender=self.agent_type,
            receiver=AgentType.LLM,
            message_type=MessageType.COMMAND,
            priority=MessagePriority.MEDIUM,
            content={
                "action": "generate_text",
                "prompt": prompt,
                "model": session.model_id
            }
        )
        
        llm_response = self.send_message_and_wait(llm_message)
        
        if not llm_response or llm_response.message_type == MessageType.ERROR:
            # If LLM generation fails, return an error message
            return ChatMessage(
                message_id=str(uuid.uuid4()),
                user_id=user_message.user_id,
                session_id=session.session_id,
                role="assistant",
                content="I'm sorry, I encountered an error while processing your question. Please try again.",
                timestamp=datetime.now()
            )
        
        # Extract generated text
        generated_text = llm_response.content.get("text", "")
        
        # Create the assistant message
        return ChatMessage(
            message_id=str(uuid.uuid4()),
            user_id=user_message.user_id,
            session_id=session.session_id,
            role="assistant",
            content=generated_text,
            timestamp=datetime.now()
        )
    
    def _handle_create_session(self, message: Message):
        """Handle session creation requests"""
        session_id = message.content.get("session_id")
        user_id = message.content.get("user_id")
        title = message.content.get("title", "New Chat")
        model_id = message.content.get("model_id", "gpt-4o")  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        document_ids = message.content.get("document_ids", [])
        
        if not session_id:
            self.send_error(message.sender, "Missing session_id parameter", message.id)
            return
        
        if not user_id:
            self.send_error(message.sender, "Missing user_id parameter", message.id)
            return
        
        # Create new session
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            title=title,
            model_id=model_id,
            document_ids=document_ids
        )
        
        # Store session
        self.sessions[session_id] = session
        
        # Send response
        self.send_response(
            message,
            {
                "status": "success",
                "session": session.dict()
            }
        )
    
    def _handle_get_session(self, message: Message):
        """Handle session retrieval requests"""
        session_id = message.content.get("session_id")
        user_id = message.content.get("user_id")
        
        if not session_id:
            self.send_error(message.sender, "Missing session_id parameter", message.id)
            return
        
        # Get session
        session = self.sessions.get(session_id)
        
        if not session:
            self.send_error(message.sender, f"Session not found: {session_id}", message.id)
            return
        
        # Verify user has permission to access this session
        if user_id and session.user_id != user_id:
            self.send_error(message.sender, "Permission denied: session belongs to another user", message.id)
            return
        
        # Send response
        self.send_response(
            message,
            {
                "session": session.dict(),
                "messages": [msg.dict() for msg in session.messages]
            }
        )
    
    def _handle_list_sessions(self, message: Message):
        """Handle request to list all sessions for a user"""
        user_id = message.content.get("user_id")
        
        if not user_id:
            self.send_error(message.sender, "Missing user_id parameter", message.id)
            return
        
        # Filter sessions by user_id
        user_sessions = [
            session.dict(exclude={"messages"})  # Exclude messages to reduce response size
            for session in self.sessions.values()
            if session.user_id == user_id
        ]
        
        # Send response
        self.send_response(
            message,
            {
                "sessions": user_sessions
            }
        )
    
    def _handle_delete_session(self, message: Message):
        """Handle session deletion requests"""
        session_id = message.content.get("session_id")
        user_id = message.content.get("user_id")
        
        if not session_id:
            self.send_error(message.sender, "Missing session_id parameter", message.id)
            return
        
        # Get session
        session = self.sessions.get(session_id)
        
        if not session:
            self.send_error(message.sender, f"Session not found: {session_id}", message.id)
            return
        
        # Verify user has permission to delete this session
        if user_id and session.user_id != user_id:
            self.send_error(message.sender, "Permission denied: session belongs to another user", message.id)
            return
        
        # Delete session
        del self.sessions[session_id]
        
        # Send response
        self.send_response(
            message,
            {
                "status": "success",
                "session_id": session_id
            }
        )
