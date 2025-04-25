from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field


class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    LLM = "llm"
    DOCUMENT_PROCESSING = "document_processing"
    INFORMATION_RETRIEVAL = "information_retrieval"
    DIALOGUE = "dialogue"
    SECURITY = "security"


class MessageType(str, Enum):
    COMMAND = "command"
    RESPONSE = "response"
    ERROR = "error"
    EVENT = "event"
    DATA = "data"


class MessagePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: f"{datetime.now().timestamp()}")
    sender: AgentType
    receiver: AgentType
    message_type: MessageType
    priority: MessagePriority = MessagePriority.MEDIUM
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None


class DocumentMetadata(BaseModel):
    filename: str
    file_type: str
    upload_timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str
    num_pages: Optional[int] = None
    num_chunks: Optional[int] = None
    size_bytes: Optional[int] = None
    description: Optional[str] = None
    document_id: str = Field(default_factory=lambda: f"{datetime.now().timestamp()}")


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    page_number: Optional[int] = None
    chunk_number: int


class User(BaseModel):
    user_id: str
    username: str
    password_hash: str
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    documents: List[str] = []  # List of document_ids
    preferences: Dict[str, Any] = {}


class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: f"{datetime.now().timestamp()}")
    user_id: str
    session_id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    document_ids: List[str] = []
    citations: List[Dict[str, Any]] = []


class ChatSession(BaseModel):
    session_id: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    title: Optional[str] = None
    document_ids: List[str] = []
    model_id: str
    messages: List[ChatMessage] = []


class RetrievalResult(BaseModel):
    document_id: str
    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    score: float


class LLMConfig(BaseModel):
    model_id: str
    provider: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    additional_params: Dict[str, Any] = {}


class AgentConfig(BaseModel):
    agent_type: AgentType
    enabled: bool = True
    config: Dict[str, Any] = {}
