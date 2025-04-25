import logging
from typing import Dict, List, Any, Optional
import uuid
import time

from schema import AgentType, Message, MessageType, DocumentChunk, RetrievalResult
from core.agents.base_agent import BaseAgent
from core.rag.retriever import VectorRetriever
from infrastructure.messaging.message_broker import MessageBroker


class InformationRetrievalAgent(BaseAgent):
    """
    The information retrieval agent is responsible for managing the vector store
    and retrieving relevant document chunks for queries.
    """
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker, **kwargs):
        """Initialize the information retrieval agent"""
        super().__init__(agent_type, message_broker)
        self.logger = logging.getLogger("agent.information_retrieval")
        
        # Initialize components
        self.retriever = VectorRetriever()
        
        # Query cache (simple in-memory cache for demonstration)
        self.query_cache: Dict[str, Dict[str, Any]] = {}
    
    def handle_message(self, message: Message):
        """Handle messages sent to the information retrieval agent"""
        if message.message_type == MessageType.COMMAND:
            self._handle_command(message)
    
    def _handle_command(self, message: Message):
        """Handle command messages"""
        action = message.content.get("action")
        
        if action == "retrieve":
            self._handle_retrieve(message)
        elif action == "index_document":
            self._handle_index_document(message)
        elif action == "remove_document":
            self._handle_remove_document(message)
        elif action == "clear_cache":
            self._handle_clear_cache(message)
        else:
            self.send_error(
                message.sender,
                f"Unknown action: {action}",
                message.id
            )
    
    def _handle_retrieve(self, message: Message):
        """Handle retrieval requests"""
        query = message.content.get("query")
        filters = message.content.get("filters", {})
        num_results = message.content.get("num_results", 5)
        use_cache = message.content.get("use_cache", True)
        
        if not query:
            self.send_error(message.sender, "Missing query parameter", message.id)
            return
        
        # Check cache if enabled
        cache_key = f"{query}_{str(filters)}_{num_results}"
        if use_cache and cache_key in self.query_cache:
            cache_entry = self.query_cache[cache_key]
            age = time.time() - cache_entry["timestamp"]
            
            # Use cache if it's less than 5 minutes old
            if age < 300:
                self.logger.info(f"Using cached results for query: {query}")
                self.send_response(message, cache_entry["results"])
                return
        
        try:
            # Retrieve results
            results = self.retriever.retrieve(
                query=query,
                filters=filters,
                k=num_results
            )
            
            # Format results
            formatted_results = [
                RetrievalResult(
                    document_id=result["document_id"],
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    metadata=result["metadata"],
                    score=result["score"]
                ).dict()
                for result in results
            ]
            
            # Cache results
            self.query_cache[cache_key] = {
                "results": {"results": formatted_results},
                "timestamp": time.time()
            }
            
            # Send response
            self.send_response(message, {"results": formatted_results})
            
        except Exception as e:
            self.logger.error(f"Error retrieving documents: {str(e)}")
            self.send_error(
                message.sender,
                f"Error retrieving documents: {str(e)}",
                message.id
            )
    
    def _handle_index_document(self, message: Message):
        """Handle document indexing requests"""
        document_id = message.content.get("document_id")
        chunks_data = message.content.get("chunks", [])
        
        if not document_id:
            self.send_error(message.sender, "Missing document_id parameter", message.id)
            return
        
        if not chunks_data:
            self.send_error(message.sender, "Missing chunks parameter", message.id)
            return
        
        try:
            # Convert chunk data to DocumentChunk objects
            chunks = [DocumentChunk(**chunk_data) for chunk_data in chunks_data]
            
            # Index chunks in the vector store
            self.retriever.add_documents(chunks)
            
            # Send response
            self.send_response(
                message,
                {
                    "status": "success",
                    "document_id": document_id,
                    "num_chunks_indexed": len(chunks)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error indexing document: {str(e)}")
            self.send_error(
                message.sender,
                f"Error indexing document: {str(e)}",
                message.id
            )
    
    def _handle_remove_document(self, message: Message):
        """Handle document removal requests"""
        document_id = message.content.get("document_id")
        
        if not document_id:
            self.send_error(message.sender, "Missing document_id parameter", message.id)
            return
        
        try:
            # Remove document from vector store
            num_removed = self.retriever.remove_document(document_id)
            
            # Clear relevant cache entries (simple implementation)
            self.query_cache = {}
            
            # Send response
            self.send_response(
                message,
                {
                    "status": "success",
                    "document_id": document_id,
                    "num_chunks_removed": num_removed
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error removing document: {str(e)}")
            self.send_error(
                message.sender,
                f"Error removing document: {str(e)}",
                message.id
            )
    
    def _handle_clear_cache(self, message: Message):
        """Handle cache clearing requests"""
        query_pattern = message.content.get("query_pattern")
        
        if query_pattern:
            # Clear only matching cache entries
            keys_to_remove = [
                key for key in self.query_cache.keys()
                if query_pattern in key
            ]
            for key in keys_to_remove:
                del self.query_cache[key]
            
            self.send_response(
                message,
                {
                    "status": "success",
                    "num_entries_cleared": len(keys_to_remove)
                }
            )
        else:
            # Clear all cache entries
            num_entries = len(self.query_cache)
            self.query_cache = {}
            
            self.send_response(
                message,
                {
                    "status": "success",
                    "num_entries_cleared": num_entries
                }
            )
