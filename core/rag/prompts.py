from typing import List, Optional, Dict, Any


class RAGPromptTemplates:
    """
    Templates for Retrieval Augmented Generation prompts.
    """
    
    def __init__(self):
        """Initialize the prompt templates"""
        pass
    
    def get_rag_prompt(
        self,
        query: str,
        context: List[str],
        chat_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate a prompt for RAG-based question answering
        
        Parameters:
        - query: The user's question
        - context: List of context chunks from retrieval
        - chat_history: Optional conversation history
        
        Returns:
        - Formatted prompt string
        """
        # Format context into a single string
        context_str = "\n\n---\n\n".join([f"Context {i+1}:\n{c}" for i, c in enumerate(context)])
        
        # Format chat history if provided
        history_str = ""
        if chat_history and len(chat_history) > 0:
            history_lines = []
            for msg in chat_history[-5:]:  # Use last 5 messages only
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role and content:
                    history_lines.append(f"{role.capitalize()}: {content}")
            
            history_str = "\n".join(history_lines)
            history_str = f"\nPrevious conversation:\n{history_str}\n"
        
        # Construct prompt
        prompt = f"""You are an intelligent assistant that helps users find information in documents.
Answer the user's question based ONLY on the provided context. If the context doesn't contain the information needed to answer the question, say "I don't have enough information to answer this question." Do not make up information that is not in the context.

{history_str}
Here is the relevant information from the documents:

{context_str}

User's question: {query}

Provide a comprehensive and accurate answer to the question based strictly on the provided context. If you need to cite specific parts of the context, do so. If the answer requires information not in the context, state that clearly.
"""
        
        return prompt
    
    def get_conversation_prompt(
        self,
        query: str,
        conversation_history: Optional[str] = None
    ) -> str:
        """
        Generate a prompt for conversational responses without RAG
        
        Parameters:
        - query: The user's question
        - conversation_history: Optional string with conversation history
        
        Returns:
        - Formatted prompt string
        """
        history_part = ""
        if conversation_history:
            history_part = f"\nHere is the conversation history:\n{conversation_history}\n"
        
        prompt = f"""You are IARA, an intelligent assistant. Respond to the user's message in a helpful and conversational way.

{history_part}
User's message: {query}

Provide a helpful response:
"""
        
        return prompt
    
    def get_reranking_prompt(self, query: str, context: str) -> str:
        """
        Generate a prompt for reranking retrieved passages
        
        Parameters:
        - query: The user's question
        - context: A context passage to evaluate
        
        Returns:
        - Formatted prompt string
        """
        prompt = f"""On a scale from 1 to 10, rate how relevant the following passage is to the question.
        
Question: {query}

Passage: {context}

Rating (1-10):
"""
        
        return prompt
