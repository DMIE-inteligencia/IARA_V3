import logging
import hashlib
import uuid
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from schema import AgentType, Message, MessageType
from core.agents.base_agent import BaseAgent
from infrastructure.messaging.message_broker import MessageBroker
from infrastructure.database.connection import SessionLocal
from infrastructure.database.models import User as DBUser  # Renomeado para evitar conflito
from infrastructure.database.repository import UserRepository


class SecurityAgent(BaseAgent):
    """
    The security agent is responsible for authentication, authorization,
    and security-related functionalities in the system.
    """
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker, **kwargs):
        """Initialize the security agent"""
        super().__init__(agent_type, message_broker)
        self.logger = logging.getLogger("agent.security")
        
        # Dicionário para armazenar sessões ativas (ainda mantemos em memória por eficiência)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Inicializar o banco de dados e criar usuário admin
        from infrastructure.database.connection import init_db
        try:
            init_db()
            self.logger.info("Banco de dados inicializado")
            self._create_default_admin()
        except Exception as e:
            self.logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
    
    def _create_default_admin(self):
        """Create a default admin user for testing"""
        admin_username = "admin"
        
        # Verificar se o usuário admin já existe
        with SessionLocal() as db:
            user_repo = UserRepository(db)
            admin_user = user_repo.get_user_by_username(admin_username)
            
            if not admin_user:
                # Criar o usuário admin se não existir
                password = "password"
                password_hash = self._hash_password(password)
                
                try:
                    user_repo.create_user(
                        username=admin_username,
                        password_hash=password_hash,
                        email="admin@iara.com.br"
                    )
                    self.logger.info("Usuário administrador criado com sucesso")
                except Exception as e:
                    self.logger.error(f"Erro ao criar usuário administrador: {str(e)}")
    
    def _hash_password(self, password: str) -> str:
        """Create a secure hash of a password"""
        # In a real implementation, this would use a proper password hashing algorithm
        # with salt, like bcrypt, Argon2, or PBKDF2
        return hashlib.sha256(password.encode()).hexdigest()
    
    def handle_message(self, message: Message):
        """Handle messages sent to the security agent"""
        if message.message_type == MessageType.COMMAND:
            self._handle_command(message)
    
    def _handle_command(self, message: Message):
        """Handle command messages"""
        action = message.content.get("action")
        
        if action == "authenticate":
            self._handle_authenticate(message)
        elif action == "register_user":
            self._handle_register_user(message)
        elif action == "validate_session":
            self._handle_validate_session(message)
        elif action == "logout":
            self._handle_logout(message)
        elif action == "get_user":
            self._handle_get_user(message)
        elif action == "update_user":
            self._handle_update_user(message)
        else:
            self.send_error(
                message.sender,
                f"Unknown action: {action}",
                message.id
            )
    
    def _handle_authenticate(self, message: Message):
        """Handle authentication requests"""
        username = message.content.get("username")
        password = message.content.get("password")
        
        if not username or not password:
            self.send_error(message.sender, "Nome de usuário ou senha ausentes", message.id)
            return
        
        # Buscar usuário no banco de dados
        try:
            with SessionLocal() as db:
                user_repo = UserRepository(db)
                user = user_repo.get_user_by_username(username)
                
                if not user:
                    self.send_error(message.sender, "Nome de usuário ou senha inválidos", message.id)
                    return
                
                # Verificar senha
                password_hash = self._hash_password(password)
                if user.password_hash != password_hash:
                    self.send_error(message.sender, "Nome de usuário ou senha inválidos", message.id)
                    return
                
                # Criar sessão
                session_id = str(uuid.uuid4())
                expires_at = datetime.now() + timedelta(hours=24)
                
                self.active_sessions[session_id] = {
                    "user_id": user.id,
                    "expires_at": expires_at
                }
                
                # Atualizar último login
                user_repo.update_user(user.id, {"last_login": datetime.now()})
                
                # Enviar resposta
                self.send_response(
                    message,
                    {
                        "status": "success",
                        "user_id": user.id,
                        "session_id": session_id,
                        "username": user.username,
                        "expires_at": expires_at.isoformat()
                    }
                )
        except Exception as e:
            self.logger.error(f"Erro durante autenticação: {str(e)}")
            self.send_error(message.sender, "Erro durante autenticação", message.id)
    
    def _handle_register_user(self, message: Message):
        """Handle user registration requests"""
        username = message.content.get("username")
        password = message.content.get("password")
        email = message.content.get("email")
        
        if not username or not password:
            self.send_error(message.sender, "Nome de usuário ou senha ausentes", message.id)
            return
        
        try:
            with SessionLocal() as db:
                user_repo = UserRepository(db)
                
                # Verificar se o nome de usuário já existe
                existing_user = user_repo.get_user_by_username(username)
                if existing_user:
                    self.send_error(message.sender, "Nome de usuário já existe", message.id)
                    return
                
                # Criar hash da senha
                password_hash = self._hash_password(password)
                
                # Criar usuário no banco de dados
                user = user_repo.create_user(
                    username=username,
                    password_hash=password_hash,
                    email=email
                )
                
                # Enviar resposta
                self.send_response(
                    message,
                    {
                        "status": "success",
                        "user_id": user.id,
                        "username": username
                    }
                )
        except Exception as e:
            self.logger.error(f"Erro ao registrar usuário: {str(e)}")
            self.send_error(message.sender, "Erro ao registrar usuário", message.id)
    
    def _handle_validate_session(self, message: Message):
        """Handle session validation requests"""
        session_id = message.content.get("session_id")
        
        if not session_id:
            self.send_error(message.sender, "Parâmetro session_id ausente", message.id)
            return
        
        # Verificar se a sessão existe
        if session_id not in self.active_sessions:
            self.send_error(message.sender, "Sessão inválida", message.id)
            return
        
        # Verificar se a sessão expirou
        session = self.active_sessions[session_id]
        if datetime.now() > session["expires_at"]:
            # Remover sessão expirada
            del self.active_sessions[session_id]
            self.send_error(message.sender, "Sessão expirada", message.id)
            return
        
        # Obter usuário do banco de dados
        user_id = session["user_id"]
        
        try:
            with SessionLocal() as db:
                user_repo = UserRepository(db)
                user = user_repo.get_user_by_id(user_id)
                
                if not user:
                    # Isso não deveria acontecer, mas por precaução
                    del self.active_sessions[session_id]
                    self.send_error(message.sender, "Usuário inválido na sessão", message.id)
                    return
                
                # Enviar resposta
                self.send_response(
                    message,
                    {
                        "status": "valid",
                        "user_id": user_id,
                        "username": user.username,
                        "expires_at": session["expires_at"].isoformat()
                    }
                )
        except Exception as e:
            self.logger.error(f"Erro ao validar sessão: {str(e)}")
            self.send_error(message.sender, "Erro ao validar sessão", message.id)
    
    def _handle_logout(self, message: Message):
        """Handle logout requests"""
        session_id = message.content.get("session_id")
        
        if not session_id:
            self.send_error(message.sender, "Parâmetro session_id ausente", message.id)
            return
        
        # Remover sessão se existir
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        # Enviar resposta
        self.send_response(
            message,
            {
                "status": "success"
            }
        )
    
    def _handle_get_user(self, message: Message):
        """Handle user retrieval requests"""
        user_id = message.content.get("user_id")
        
        if not user_id:
            self.send_error(message.sender, "Parâmetro user_id ausente", message.id)
            return
        
        try:
            with SessionLocal() as db:
                user_repo = UserRepository(db)
                user = user_repo.get_user_by_id(user_id)
                
                if not user:
                    self.send_error(message.sender, f"Usuário não encontrado: {user_id}", message.id)
                    return
                
                # Enviar resposta (nunca enviar o hash da senha)
                user_data = user.to_dict()
                self.send_response(message, {"user": user_data})
        except Exception as e:
            self.logger.error(f"Erro ao obter usuário: {str(e)}")
            self.send_error(message.sender, "Erro ao obter usuário", message.id)
    
    def _handle_update_user(self, message: Message):
        """Handle user update requests"""
        user_id = message.content.get("user_id")
        updates = message.content.get("updates", {})
        
        if not user_id:
            self.send_error(message.sender, "Parâmetro user_id ausente", message.id)
            return
        
        if not updates:
            self.send_error(message.sender, "Parâmetro updates ausente", message.id)
            return
        
        try:
            with SessionLocal() as db:
                user_repo = UserRepository(db)
                user = user_repo.get_user_by_id(user_id)
                
                if not user:
                    self.send_error(message.sender, f"Usuário não encontrado: {user_id}", message.id)
                    return
                
                # Tratar atualização de senha separadamente
                if "password" in updates:
                    password = updates.pop("password")
                    updates["password_hash"] = self._hash_password(password)
                
                # Atualizar usuário no banco de dados
                updated_user = user_repo.update_user(user_id, updates)
                
                # Enviar resposta
                user_data = updated_user.to_dict()
                self.send_response(message, {"status": "success", "user": user_data})
        except Exception as e:
            self.logger.error(f"Erro ao atualizar usuário: {str(e)}")
            self.send_error(message.sender, f"Erro ao atualizar usuário: {str(e)}", message.id)
