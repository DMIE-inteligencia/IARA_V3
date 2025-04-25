import logging
from typing import Dict, Any, Optional, List
import threading


class StateManager:
    """
    Manages application state and provides a centralized way to share state 
    across different components and agents in the IARA system.
    """
    
    def __init__(self):
        """Initialize the state manager"""
        self.logger = logging.getLogger("state_manager")
        
        # Global state dictionary
        self._state: Dict[str, Any] = {
            "users": {},
            "documents": {},
            "chat_sessions": {},
            "agent_statuses": {},
            "system_preferences": {}
        }
        
        # Lock for thread safety
        self._lock = threading.Lock()
    
    def get_state(self, key: str) -> Any:
        """
        Get a value from the state store
        
        Parameters:
        - key: The state key to retrieve
        
        Returns:
        - The state value, or None if the key doesn't exist
        """
        with self._lock:
            path_parts = key.split('.')
            current = self._state
            
            try:
                for part in path_parts:
                    current = current[part]
                return current
            except (KeyError, TypeError):
                return None
    
    def set_state(self, key: str, value: Any) -> None:
        """
        Set a value in the state store
        
        Parameters:
        - key: The state key to set
        - value: The value to store
        """
        with self._lock:
            path_parts = key.split('.')
            current = self._state
            
            # Navigate to the parent object
            for part in path_parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[path_parts[-1]] = value
    
    def update_state(self, key: str, value: Any) -> None:
        """
        Update a dictionary value in the state store by merging
        
        Parameters:
        - key: The state key to update
        - value: The value to merge with the existing state
        """
        with self._lock:
            current_value = self.get_state(key)
            
            if current_value is None:
                # If key doesn't exist, just set it
                self.set_state(key, value)
            elif isinstance(current_value, dict) and isinstance(value, dict):
                # Merge dictionaries
                updated_value = {**current_value, **value}
                self.set_state(key, updated_value)
            elif isinstance(current_value, list) and isinstance(value, list):
                # Combine lists
                updated_value = current_value + value
                self.set_state(key, updated_value)
            else:
                # For other types, just replace
                self.set_state(key, value)
    
    def delete_state(self, key: str) -> bool:
        """
        Delete a value from the state store
        
        Parameters:
        - key: The state key to delete
        
        Returns:
        - True if the key was deleted, False otherwise
        """
        with self._lock:
            path_parts = key.split('.')
            current = self._state
            
            try:
                # Navigate to the parent object
                for part in path_parts[:-1]:
                    current = current[part]
                
                # Delete the key
                if path_parts[-1] in current:
                    del current[path_parts[-1]]
                    return True
                return False
            except (KeyError, TypeError):
                return False
    
    def get_user_documents(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all documents for a specific user
        
        Parameters:
        - user_id: The ID of the user
        
        Returns:
        - List of document metadata
        """
        documents = self.get_state("documents") or {}
        return [doc for doc in documents.values() if doc.get("user_id") == user_id]
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID
        
        Parameters:
        - document_id: The ID of the document
        
        Returns:
        - Document metadata, or None if not found
        """
        documents = self.get_state("documents") or {}
        return documents.get(document_id)
    
    def store_document(self, document_id: str, metadata: Dict[str, Any]) -> None:
        """
        Store document metadata
        
        Parameters:
        - document_id: The ID of the document
        - metadata: Document metadata
        """
        self.set_state(f"documents.{document_id}", metadata)
        
        # Also add to user's document list
        user_id = metadata.get("user_id")
        if user_id:
            user_docs = self.get_state(f"users.{user_id}.documents") or []
            if document_id not in user_docs:
                user_docs.append(document_id)
                self.set_state(f"users.{user_id}.documents", user_docs)
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete document metadata
        
        Parameters:
        - document_id: The ID of the document
        
        Returns:
        - True if the document was deleted, False otherwise
        """
        document = self.get_document(document_id)
        if not document:
            return False
        
        # Remove from user's document list
        user_id = document.get("user_id")
        if user_id:
            user_docs = self.get_state(f"users.{user_id}.documents") or []
            if document_id in user_docs:
                user_docs.remove(document_id)
                self.set_state(f"users.{user_id}.documents", user_docs)
        
        # Delete document
        return self.delete_state(f"documents.{document_id}")
    
    def get_user_chat_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all chat sessions for a specific user
        
        Parameters:
        - user_id: The ID of the user
        
        Returns:
        - List of chat session data
        """
        sessions = self.get_state("chat_sessions") or {}
        return [session for session in sessions.values() if session.get("user_id") == user_id]
    
    def get_chat_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific chat session by ID
        
        Parameters:
        - session_id: The ID of the chat session
        
        Returns:
        - Chat session data, or None if not found
        """
        sessions = self.get_state("chat_sessions") or {}
        return sessions.get(session_id)
    
    def store_chat_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """
        Store chat session data
        
        Parameters:
        - session_id: The ID of the chat session
        - session_data: Chat session data
        """
        self.set_state(f"chat_sessions.{session_id}", session_data)
    
    def delete_chat_session(self, session_id: str) -> bool:
        """
        Delete chat session data
        
        Parameters:
        - session_id: The ID of the chat session
        
        Returns:
        - True if the session was deleted, False otherwise
        """
        return self.delete_state(f"chat_sessions.{session_id}")
    
    def update_agent_status(self, agent_type: str, status: str) -> None:
        """
        Update the status of an agent
        
        Parameters:
        - agent_type: The type of the agent
        - status: The new status
        """
        self.set_state(f"agent_statuses.{agent_type}", status)
    
    def get_agent_status(self, agent_type: str) -> Optional[str]:
        """
        Get the status of an agent
        
        Parameters:
        - agent_type: The type of the agent
        
        Returns:
        - The agent status, or None if not found
        """
        return self.get_state(f"agent_statuses.{agent_type}")
    
    def get_system_preference(self, key: str, default: Any = None) -> Any:
        """
        Get a system preference
        
        Parameters:
        - key: The preference key
        - default: Default value if preference doesn't exist
        
        Returns:
        - The preference value, or the default if not found
        """
        value = self.get_state(f"system_preferences.{key}")
        return value if value is not None else default
    
    def set_system_preference(self, key: str, value: Any) -> None:
        """
        Set a system preference
        
        Parameters:
        - key: The preference key
        - value: The preference value
        """
        self.set_state(f"system_preferences.{key}", value)
