import logging
import os
from typing import Dict, Any, List, Optional
import tempfile
import uuid

from schema import AgentType, Message, MessageType, DocumentMetadata, DocumentChunk
from core.agents.base_agent import BaseAgent
from core.document_processing.loaders import DocumentLoader
from core.document_processing.splitters import TextSplitter
from core.document_processing.embeddings import EmbeddingGenerator
from infrastructure.messaging.message_broker import MessageBroker


class DocumentProcessingAgent(BaseAgent):
    """
    The document processing agent is responsible for loading, parsing,
    and processing documents for use in the RAG system.
    """
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker, **kwargs):
        """Initialize the document processing agent"""
        super().__init__(agent_type, message_broker)
        self.logger = logging.getLogger("agent.document_processing")
        
        # Initialize components
        self.document_loader = DocumentLoader()
        self.text_splitter = TextSplitter()
        self.embedding_generator = EmbeddingGenerator()
        
        # In-memory document store (would be replaced with a database in production)
        self.documents: Dict[str, DocumentMetadata] = {}
        self.chunks: Dict[str, List[DocumentChunk]] = {}
    
    def handle_message(self, message: Message):
        """Handle messages sent to the document processing agent"""
        if message.message_type == MessageType.COMMAND:
            self._handle_command(message)
    
    def _handle_command(self, message: Message):
        """Handle command messages"""
        action = message.content.get("action")
        
        if action == "process_document":
            self._handle_process_document(message)
        elif action == "get_document":
            self._handle_get_document(message)
        elif action == "get_user_documents":
            self._handle_get_user_documents(message)
        elif action == "delete_document":
            self._handle_delete_document(message)
        else:
            self.send_error(
                message.sender,
                f"Unknown action: {action}",
                message.id
            )
    
    def _handle_process_document(self, message: Message):
        """Handle document processing requests"""
        file_path = message.content.get("file_path")
        metadata_dict = message.content.get("metadata", {})
        
        if not file_path:
            self.send_error(message.sender, "Missing file_path parameter", message.id)
            return
        
        if not os.path.exists(file_path):
            self.send_error(message.sender, f"File not found: {file_path}", message.id)
            return
        
        try:
            # Parse metadata
            metadata = DocumentMetadata(**metadata_dict)
            
            # Load document
            document_text = self.document_loader.load_document(file_path)
            
            # Split document into chunks
            chunks = self.text_splitter.split_text(document_text)
            
            # Create DocumentChunk objects
            document_chunks = []
            for i, chunk_text in enumerate(chunks):
                chunk = DocumentChunk(
                    chunk_id=f"chunk_{uuid.uuid4()}",
                    document_id=metadata.document_id,
                    content=chunk_text,
                    chunk_number=i,
                    page_number=None  # Would be set if available from loader
                )
                document_chunks.append(chunk)
            
            # Generate embeddings for chunks
            self._generate_embeddings_for_chunks(document_chunks)
            
            # Update metadata
            metadata.num_chunks = len(document_chunks)
            
            # Store document and chunks
            self.documents[metadata.document_id] = metadata
            self.chunks[metadata.document_id] = document_chunks
            
            # Create the information retrieval agent message to index the document
            retrieval_message = Message(
                sender=self.agent_type,
                receiver=AgentType.INFORMATION_RETRIEVAL,
                message_type=MessageType.COMMAND,
                content={
                    "action": "index_document",
                    "document_id": metadata.document_id,
                    "chunks": [chunk.dict() for chunk in document_chunks]
                }
            )
            self.send_message(retrieval_message)
            
            # Send successful response
            self.send_response(
                message,
                {
                    "status": "success",
                    "document_id": metadata.document_id,
                    "metadata": {
                        "num_chunks": metadata.num_chunks,
                        "num_pages": metadata.num_pages
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}")
            self.send_error(
                message.sender,
                f"Error processing document: {str(e)}",
                message.id
            )
    
    def _generate_embeddings_for_chunks(self, chunks: List[DocumentChunk]):
        """Generate embeddings for document chunks"""
        # Group texts for batch processing
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embedding_generator.generate_embeddings(texts)
        
        # Assign embeddings to chunks
        for i, chunk in enumerate(chunks):
            chunk.embedding = embeddings[i]
    
    def _handle_get_document(self, message: Message):
        """Handle request to get document data"""
        document_id = message.content.get("document_id")
        include_chunks = message.content.get("include_chunks", False)
        include_embeddings = message.content.get("include_embeddings", False)
        
        if not document_id:
            self.send_error(message.sender, "Missing document_id parameter", message.id)
            return
        
        document = self.documents.get(document_id)
        if not document:
            self.send_error(message.sender, f"Document not found: {document_id}", message.id)
            return
        
        response_data = {
            "document": document.dict()
        }
        
        if include_chunks:
            chunks = self.chunks.get(document_id, [])
            
            if not include_embeddings:
                # Remove embeddings from chunks if not requested
                chunks_data = []
                for chunk in chunks:
                    chunk_dict = chunk.dict()
                    if "embedding" in chunk_dict:
                        del chunk_dict["embedding"]
                    chunks_data.append(chunk_dict)
            else:
                chunks_data = [chunk.dict() for chunk in chunks]
            
            response_data["chunks"] = chunks_data
        
        self.send_response(message, response_data)
    
    def _handle_get_user_documents(self, message: Message):
        """Handle request to get all documents for a user"""
        user_id = message.content.get("user_id")
        
        if not user_id:
            self.send_error(message.sender, "Missing user_id parameter", message.id)
            return
        
        # Filter documents by user_id
        user_documents = [
            doc.dict() for doc in self.documents.values()
            if doc.user_id == user_id
        ]
        
        self.send_response(message, {"documents": user_documents})
    
    def _handle_delete_document(self, message: Message):
        """Handle request to delete a document"""
        document_id = message.content.get("document_id")
        user_id = message.content.get("user_id")
        
        if not document_id:
            self.send_error(message.sender, "Missing document_id parameter", message.id)
            return
        
        document = self.documents.get(document_id)
        if not document:
            self.send_error(message.sender, f"Document not found: {document_id}", message.id)
            return
        
        # Check if user has permission to delete this document
        if user_id and document.user_id != user_id:
            self.send_error(message.sender, "Permission denied: document belongs to another user", message.id)
            return
        
        # Delete document and chunks
        del self.documents[document_id]
        if document_id in self.chunks:
            del self.chunks[document_id]
        
        # Create the information retrieval agent message to remove the document
        retrieval_message = Message(
            sender=self.agent_type,
            receiver=AgentType.INFORMATION_RETRIEVAL,
            message_type=MessageType.COMMAND,
            content={
                "action": "remove_document",
                "document_id": document_id
            }
        )
        self.send_message(retrieval_message)
        
        # Send successful response
        self.send_response(
            message,
            {
                "status": "success",
                "document_id": document_id
            }
        )
