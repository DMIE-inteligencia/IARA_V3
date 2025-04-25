import streamlit as st
from typing import List, Dict, Any
import uuid
import os
from datetime import datetime

from schema import ChatMessage, MessageType, AgentType, MessagePriority, Message
from core.agents.agent_factory import AgentFactory


class UserChatInterface:
    """Interface de chat simplificada para usuários comuns"""
    
    def __init__(self):
        """Initialize the chat interface component"""
        self.orchestrator = st.session_state.agent_factory.get_agent(AgentType.ORCHESTRATOR)
        self.dialogue_agent = st.session_state.agent_factory.get_agent(AgentType.DIALOGUE)
        self.doc_processing_agent = st.session_state.agent_factory.get_agent(AgentType.DOCUMENT_PROCESSING)
    
    def create_new_session(self):
        """Create a new chat session"""
        session_id = f"session_{uuid.uuid4()}"
        st.session_state.current_session_id = session_id
        st.session_state.chat_history = []
        
        # Notify the dialogue agent about the new session
        message = Message(
            sender=AgentType.ORCHESTRATOR,
            receiver=AgentType.DIALOGUE,
            message_type=MessageType.COMMAND,
            priority=MessagePriority.HIGH,
            content={
                "action": "create_session",
                "session_id": session_id,
                "user_id": st.session_state.user_id
            }
        )
        
        self.orchestrator.send_message(message)
        return session_id
    
    def load_session(self, session_id: str):
        """Load an existing chat session"""
        # Request the session history from the dialogue agent
        message = Message(
            sender=AgentType.ORCHESTRATOR,
            receiver=AgentType.DIALOGUE,
            message_type=MessageType.COMMAND,
            content={
                "action": "get_session",
                "session_id": session_id,
                "user_id": st.session_state.user_id
            }
        )
        
        response = self.orchestrator.send_message_and_wait(message)
        
        if response and response.message_type != MessageType.ERROR:
            st.session_state.current_session_id = session_id
            st.session_state.chat_history = response.content.get("messages", [])
        else:
            st.error("Falha ao carregar conversa")
    
    def send_message(self, user_input: str):
        """Send a user message to the system and get a response"""
        if not st.session_state.current_session_id:
            self.create_new_session()
        
        # Create user message object
        user_message = ChatMessage(
            user_id=st.session_state.user_id,
            session_id=st.session_state.current_session_id,
            role="user",
            content=user_input
        )
        
        # Add to local chat history
        st.session_state.chat_history.append(user_message)
        
        # Create message for dialogue agent
        message = Message(
            sender=AgentType.ORCHESTRATOR,
            receiver=AgentType.DIALOGUE,
            message_type=MessageType.COMMAND,
            content={
                "action": "process_user_message",
                "message": user_message.dict(),
                "session_id": st.session_state.current_session_id,
                "user_id": st.session_state.user_id,
                "documents": st.session_state.documents
            }
        )
        
        # Send message and wait for response
        response = self.orchestrator.send_message_and_wait(message)
        
        if response and response.message_type != MessageType.ERROR:
            # Extract the assistant message from the response
            assistant_message = ChatMessage(**response.content.get("message"))
            
            # Add to local chat history
            st.session_state.chat_history.append(assistant_message)
            
            return assistant_message
        else:
            # Handle error case
            error_message = ChatMessage(
                user_id=st.session_state.user_id,
                session_id=st.session_state.current_session_id,
                role="assistant",
                content="Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente."
            )
            st.session_state.chat_history.append(error_message)
            return error_message
    
    def upload_document(self, file):
        """Handle document upload and processing"""
        try:
            # Create unique document ID
            document_id = f"doc_{uuid.uuid4()}"
            
            # Save the file temporarily
            file_path = f"/tmp/{file.name}"
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            
            # Prepare document metadata
            metadata = {
                "filename": file.name,
                "file_type": file.type,
                "user_id": st.session_state.user_id,
                "size_bytes": file.size,
                "document_id": document_id
            }
            
            # Create message for document processing agent
            message = Message(
                sender=AgentType.ORCHESTRATOR,
                receiver=AgentType.DOCUMENT_PROCESSING,
                message_type=MessageType.COMMAND,
                priority=MessagePriority.MEDIUM,
                content={
                    "action": "process_document",
                    "file_path": file_path,
                    "metadata": metadata
                }
            )
            
            # Send message and wait for response
            with st.spinner("Processando documento..."):
                response = self.orchestrator.send_message_and_wait(message)
            
            # Check response and update UI
            if response and response.message_type != MessageType.ERROR:
                # Add document to session state
                st.session_state.documents.append(document_id)
                return True
            else:
                return False
                
        except Exception as e:
            st.error(f"Erro ao carregar documento: {str(e)}")
            return False
        finally:
            # Clean up temporary file
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)

    def render(self):
        """Render the simplified user chat interface"""
        # Inicializar estrutura de dados para conversas
        if "user_chat_history" not in st.session_state:
            st.session_state.user_chat_history = []
        if "user_chats" not in st.session_state:
            st.session_state.user_chats = [
                {"id": "chat_1", "title": "Nova conversa", "active": True}
            ]
            
        # Layout de duas colunas: sidebar à esquerda e chat à direita
        col1, col2 = st.columns([1, 4])
        
        # Sidebar simplificada (coluna 1)
        with col1:
            # Logo
            st.markdown("""
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="font-size: 2rem; margin-bottom: 0;">IARA</h1>
                </div>
            """, unsafe_allow_html=True)
            
            # Botão de nova conversa
            if st.button("+ Nova conversa", use_container_width=True):
                # Limpar histórico atual
                st.session_state.chat_history = []
                self.create_new_session()
                st.rerun()
            
            # Lista de conversas (simplificada)
            st.markdown("### Conversas")
            
            # Mostrar conversas anteriores
            for i in range(min(5, len(st.session_state.user_chats))):
                chat = st.session_state.user_chats[i]
                if st.button(f"{chat['title']}", key=f"chat_{i}", use_container_width=True):
                    self.load_session(chat["id"])
                    st.rerun()
            
            # Separador
            st.markdown("---")
            
            # Informações do usuário no rodapé
            st.markdown(f"Conectado como: **{st.session_state.user_id.replace('user_', '')}**")
            
            # Botão de logout
            if st.button("Sair", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.authenticated = False
                st.rerun()
        
        # Área principal de chat (coluna 2)
        with col2:
            # Container para as mensagens
            chat_container = st.container(height=500)
            
            with chat_container:
                # Exibir mensagens do histórico
                if not st.session_state.chat_history:
                    # Mensagem de boas-vindas
                    st.markdown("""
                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 350px; text-align: center;">
                            <div style="font-size: 4rem; margin-bottom: 1rem;">
                                🤖
                            </div>
                            <h2>IARA - Assistente IA</h2>
                            <p style="color: #666; max-width: 500px; margin: 0 auto;">
                                Olá! Sou a IARA, sua assistente de IA. Posso responder perguntas, criar conteúdo
                                e analisar documentos para ajudar você.
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    # Renderizar cada mensagem no histórico
                    for message in st.session_state.chat_history:
                        is_user = message.role == "user"
                        
                        # Estilo diferente para usuário vs. assistente
                        if is_user:
                            st.markdown(f"""
                            <div style="display: flex; margin-bottom: 12px;">
                                <div style="background-color: #f0f2f6; border-radius: 8px; padding: 10px 16px; max-width: 80%;">
                                    <div style="font-weight: bold; margin-bottom: 5px;">Você</div>
                                    <div>{message.content}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="display: flex; margin-bottom: 12px;">
                                <div style="background-color: #f7f7f7; border-radius: 8px; padding: 10px 16px; max-width: 80%;">
                                    <div style="font-weight: bold; margin-bottom: 5px; color: #10a37f;">IARA</div>
                                    <div>{message.content}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Mostrar citações se houver
                            if message.citations and len(message.citations) > 0:
                                with st.expander("Ver fontes dos documentos"):
                                    for i, citation in enumerate(message.citations):
                                        st.markdown(f"""
                                        <div style="border-left: 3px solid #10a37f; padding-left: 10px; margin-bottom: 8px;">
                                            <div><strong>Fonte {i+1}:</strong> {citation.get('content', '')}</div>
                                            <div style="color: #888; font-size: 0.8rem;">Documento: {citation.get('document_id', '')}</div>
                                        </div>
                                        """, unsafe_allow_html=True)
            
            # Área de input fixa na parte inferior
            input_container = st.container(border=True)
            
            with input_container:
                # Upload de arquivos integrado
                col_upload, col_input, col_send = st.columns([1, 8, 1])
                
                with col_upload:
                    uploaded_file = st.file_uploader("Anexar arquivo", 
                                                    type=["pdf", "docx", "txt"], 
                                                    label_visibility="collapsed",
                                                    key="chat_file")
                    if uploaded_file:
                        if self.upload_document(uploaded_file):
                            st.success(f"Arquivo '{uploaded_file.name}' carregado com sucesso!")
                            # Limpar o uploader depois de processar
                            st.session_state["chat_file"] = None
                            st.rerun()
                        else:
                            st.error("Falha ao processar o arquivo")
                
                with col_input:
                    # Campo de entrada de texto
                    user_input = st.text_area("Envie uma mensagem...", 
                                             height=50, 
                                             placeholder="Digite sua mensagem para IARA...",
                                             label_visibility="collapsed",
                                             key="user_msg_input")
                
                with col_send:
                    # Botão de enviar
                    send_btn = st.button("Enviar", key="send_msg", use_container_width=True)
                    if send_btn and user_input:
                        with st.spinner("Processando..."):
                            self.send_message(user_input)
                        
                        # Limpar entrada após enviar
                        st.session_state["user_msg_input"] = ""
                        st.rerun()