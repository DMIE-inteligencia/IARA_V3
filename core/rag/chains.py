import logging
from typing import Dict, List, Any, Optional

from schema import AgentType, Message, MessageType
from core.rag.prompts import RAGPromptTemplates


class RAGChain:
    """
    Retrieval Augmented Generation chain that combines document retrieval
    with language model generation.
    """
    
    def __init__(self):
        """Initialize the RAG chain"""
        self.logger = logging.getLogger("rag_chain")
        self.prompt_templates = RAGPromptTemplates()
    
    def run(
        self,
        query: str,
        retriever_agent: Any,
        llm_agent: Any,
        document_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Run the RAG chain on a query
        
        Parameters:
        - query: The user's question
        - retriever_agent: Agent for information retrieval
        - llm_agent: Agent for text generation
        - document_ids: Optional list of document IDs to restrict search
        - filters: Additional filters for retrieval
        - num_results: Number of chunks to retrieve
        
        Returns:
        - Dictionary with generated answer and source information
        """
        try:
            # Prepare retrieval filters
            if not filters:
                filters = {}
            
            if document_ids:
                filters["document_id"] = document_ids
            
            # Create retrieval message
            retrieval_message = Message(
                sender=AgentType.DIALOGUE,
                receiver=AgentType.INFORMATION_RETRIEVAL,
                message_type=MessageType.COMMAND,
                content={
                    "action": "retrieve",
                    "query": query,
                    "filters": filters,
                    "num_results": num_results
                }
            )
            
            # Send message and get response
            retrieval_response = retriever_agent.send_message_and_wait(retrieval_message)
            
            if not retrieval_response or retrieval_response.message_type == MessageType.ERROR:
                return {
                    "answer": "I couldn't find relevant information to answer your question.",
                    "sources": [],
                    "error": "Retrieval failed"
                }
            
            # Extract results
            results = retrieval_response.content.get("results", [])
            
            if not results:
                return {
                    "answer": "I don't have enough information in the documents to answer this question.",
                    "sources": [],
                    "error": "No relevant information found"
                }
            
            # Prepare context for LLM
            context_chunks = [result["content"] for result in results]
            
            # Create the prompt with context
            prompt = self.prompt_templates.get_rag_prompt(
                query=query,
                context=context_chunks
            )
            
            # Create LLM message
            llm_message = Message(
                sender=AgentType.DIALOGUE,
                receiver=AgentType.LLM,
                message_type=MessageType.COMMAND,
                content={
                    "action": "generate_text",
                    "prompt": prompt
                }
            )
            
            # Send message and get response
            llm_response = llm_agent.send_message_and_wait(llm_message)
            
            if not llm_response or llm_response.message_type == MessageType.ERROR:
                return {
                    "answer": "I encountered an error while generating a response.",
                    "sources": [],
                    "error": "LLM generation failed"
                }
            
            # Extract generated text
            answer = llm_response.content.get("text", "")
            
            # Format sources
            sources = [
                {
                    "document_id": result["document_id"],
                    "chunk_id": result["chunk_id"],
                    "content": result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"],
                    "score": result["score"]
                }
                for result in results
            ]
            
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            self.logger.error(f"Error in RAG chain: {str(e)}")
            return {
                "answer": "An error occurred while processing your question.",
                "sources": [],
                "error": str(e)
            }
