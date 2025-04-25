import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import User, Document, DocumentChunk, ChatSession, ChatMessage

# Configuração do logger
logger = logging.getLogger("repository")

class BaseRepository:
    """Classe base para os repositórios do IARA"""
    
    def __init__(self, db: Session):
        """Inicializa o repositório com uma sessão de banco de dados"""
        self.db = db

class UserRepository(BaseRepository):
    """Repositório para operações com usuários"""
    
    def create_user(self, username: str, password_hash: str, email: Optional[str] = None) -> User:
        """Cria um novo usuário"""
        try:
            user = User(
                username=username,
                password_hash=password_hash,
                email=email
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            logger.error(f"Erro ao criar usuário: {str(e)}")
            self.db.rollback()
            raise
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Obtém um usuário pelo ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Obtém um usuário pelo nome de usuário"""
        return self.db.query(User).filter(User.username == username).first()
    
    def update_user(self, user_id: str, data: Dict[str, Any]) -> Optional[User]:
        """Atualiza os dados de um usuário"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None
            
            for key, value in data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            logger.error(f"Erro ao atualizar usuário: {str(e)}")
            self.db.rollback()
            raise
    
    def delete_user(self, user_id: str) -> bool:
        """Exclui um usuário"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            self.db.delete(user)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Erro ao excluir usuário: {str(e)}")
            self.db.rollback()
            raise

class DocumentRepository(BaseRepository):
    """Repositório para operações com documentos"""
    
    def create_document(self, document_data: Dict[str, Any]) -> Document:
        """Cria um novo documento"""
        try:
            document = Document(**document_data)
            self.db.add(document)
            self.db.commit()
            self.db.refresh(document)
            return document
        except SQLAlchemyError as e:
            logger.error(f"Erro ao criar documento: {str(e)}")
            self.db.rollback()
            raise
    
    def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """Obtém um documento pelo ID"""
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def get_documents_by_user(self, user_id: str) -> List[Document]:
        """Obtém todos os documentos de um usuário"""
        return self.db.query(Document).filter(Document.user_id == user_id).all()
    
    def update_document(self, document_id: str, data: Dict[str, Any]) -> Optional[Document]:
        """Atualiza os dados de um documento"""
        try:
            document = self.get_document_by_id(document_id)
            if not document:
                return None
            
            for key, value in data.items():
                if hasattr(document, key):
                    setattr(document, key, value)
            
            self.db.commit()
            self.db.refresh(document)
            return document
        except SQLAlchemyError as e:
            logger.error(f"Erro ao atualizar documento: {str(e)}")
            self.db.rollback()
            raise
    
    def delete_document(self, document_id: str) -> bool:
        """Exclui um documento"""
        try:
            document = self.get_document_by_id(document_id)
            if not document:
                return False
            
            self.db.delete(document)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Erro ao excluir documento: {str(e)}")
            self.db.rollback()
            raise
    
    def add_chunk(self, chunk_data: Dict[str, Any]) -> DocumentChunk:
        """Adiciona um fragmento a um documento"""
        try:
            chunk = DocumentChunk(**chunk_data)
            self.db.add(chunk)
            self.db.commit()
            self.db.refresh(chunk)
            return chunk
        except SQLAlchemyError as e:
            logger.error(f"Erro ao adicionar fragmento: {str(e)}")
            self.db.rollback()
            raise
    
    def get_chunks_by_document(self, document_id: str) -> List[DocumentChunk]:
        """Obtém todos os fragmentos de um documento"""
        return self.db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()

class ChatRepository(BaseRepository):
    """Repositório para operações com sessões de chat e mensagens"""
    
    def create_session(self, session_data: Dict[str, Any]) -> ChatSession:
        """Cria uma nova sessão de chat"""
        try:
            session = ChatSession(**session_data)
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            return session
        except SQLAlchemyError as e:
            logger.error(f"Erro ao criar sessão de chat: {str(e)}")
            self.db.rollback()
            raise
    
    def get_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        """Obtém uma sessão de chat pelo ID"""
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    def get_sessions_by_user(self, user_id: str) -> List[ChatSession]:
        """Obtém todas as sessões de chat de um usuário"""
        return self.db.query(ChatSession).filter(ChatSession.user_id == user_id).all()
    
    def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[ChatSession]:
        """Atualiza os dados de uma sessão de chat"""
        try:
            session = self.get_session_by_id(session_id)
            if not session:
                return None
            
            for key, value in data.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            self.db.commit()
            self.db.refresh(session)
            return session
        except SQLAlchemyError as e:
            logger.error(f"Erro ao atualizar sessão de chat: {str(e)}")
            self.db.rollback()
            raise
    
    def delete_session(self, session_id: str) -> bool:
        """Exclui uma sessão de chat"""
        try:
            session = self.get_session_by_id(session_id)
            if not session:
                return False
            
            self.db.delete(session)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Erro ao excluir sessão de chat: {str(e)}")
            self.db.rollback()
            raise
    
    def add_message(self, message_data: Dict[str, Any]) -> ChatMessage:
        """Adiciona uma mensagem a uma sessão de chat"""
        try:
            message = ChatMessage(**message_data)
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            return message
        except SQLAlchemyError as e:
            logger.error(f"Erro ao adicionar mensagem: {str(e)}")
            self.db.rollback()
            raise
    
    def get_messages_by_session(self, session_id: str) -> List[ChatMessage]:
        """Obtém todas as mensagens de uma sessão de chat"""
        return self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp).all()