import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from infrastructure.database.connection import Base, ModelBase

class User(Base, ModelBase):
    """Modelo de usuário para armazenamento no banco de dados"""
    
    # Colunas da tabela
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSON, default=dict)
    
    # Relacionamentos
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "user_id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "preferences": self.preferences,
            "documents": [doc.id for doc in self.documents] if self.documents else []
        }

class Document(Base, ModelBase):
    """Modelo de documento para armazenamento no banco de dados"""
    
    # Colunas da tabela
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.now)
    num_pages = Column(Integer, nullable=True)
    num_chunks = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    
    # Relacionamentos
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(filename='{self.filename}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "document_id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "user_id": self.user_id,
            "upload_timestamp": self.upload_timestamp,
            "num_pages": self.num_pages,
            "num_chunks": self.num_chunks,
            "size_bytes": self.size_bytes,
            "description": self.description
        }

class DocumentChunk(Base, ModelBase):
    """Modelo de fragmento de documento para armazenamento no banco de dados"""
    
    # Colunas da tabela
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("document.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_metadata = Column(JSON, default=dict)  # Renomeado de 'metadata' para evitar conflito com SQLAlchemy
    embedding = Column(JSON, nullable=True)  # Armazenado como JSON para compatibilidade
    page_number = Column(Integer, nullable=True)
    chunk_number = Column(Integer, nullable=False)
    
    # Relacionamentos
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(document_id='{self.document_id}', chunk_number={self.chunk_number})>"
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "chunk_id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "metadata": self.chunk_metadata,  # Mantemos o nome original na saída para compatibilidade
            "embedding": self.embedding,
            "page_number": self.page_number,
            "chunk_number": self.chunk_number
        }

class ChatSession(Base, ModelBase):
    """Modelo de sessão de chat para armazenamento no banco de dados"""
    
    # Colunas da tabela
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    title = Column(String(255), nullable=True)
    model_id = Column(String(100), nullable=False)
    
    # Relacionamentos
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id='{self.id}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "session_id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "title": self.title,
            "model_id": self.model_id,
            "messages": [msg.to_dict() for msg in self.messages] if self.messages else []
        }

class ChatMessage(Base, ModelBase):
    """Modelo de mensagem de chat para armazenamento no banco de dados"""
    
    # Colunas da tabela
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chatsession.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("user.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' ou 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    citations = Column(JSON, default=list)  # Lista de citações
    
    # Relacionamentos
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(session_id='{self.session_id}', role='{self.role}')>"
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "message_id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "citations": self.citations
        }