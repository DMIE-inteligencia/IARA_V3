import streamlit as st
from typing import List, Dict, Any
import uuid
from datetime import datetime

from schema import ChatMessage, MessageType, AgentType, MessagePriority, Message
from core.agents.agent_factory import AgentFactory


class ChatInterface:
    def __init__(self):
        """Initialize the chat interface component"""
        self.orchestrator = st.session_state.agent_factory.get_agent(AgentType.ORCHESTRATOR)
        self.dialogue_agent = st.session_state.agent_factory.get_agent(AgentType.DIALOGUE)
    
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
            st.error("Failed to load chat session")
    
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
    
    def render_message(self, message: ChatMessage):
        """Render a single chat message"""
        is_user = message.role == "user"
        
        # Define message container style
        message_container = st.container()
        
        with message_container:
            cols = st.columns([1, 10, 1])
            
            # Display the message in the middle column
            with cols[1]:
                if is_user:
                    st.write(f"**Você:** {message.content}")
                else:
                    st.write(f"**IARA:** {message.content}")
                    
                    # Display citations if they exist
                    if message.citations and len(message.citations) > 0:
                        with st.expander("Ver Fontes"):
                            for i, citation in enumerate(message.citations):
                                st.write(f"**Fonte {i+1}:** {citation.get('content', '')} (Documento: {citation.get('document_id', 'Desconhecido')})")
    
    def render(self):
        """Render the chat interface"""
        # Modelo selecionado atualmente (recebido via session_state)
        current_model = st.session_state.selected_model
        
        # Configuração de cores baseada no modelo
        model_colors = {
            "GPT-4o": "#10a37f",     # Verde OpenAI
            "Claude-3": "#8c31e8",   # Roxo Anthropic
            "Llama-3": "#1877f2",    # Azul Meta
            "Grok-2": "#ff3c00"      # Laranja xAI
        }
        model_color = model_colors.get(current_model, "#10a37f")
        
        # Container principal para o chat
        st.container(height=10)  # Espaço superior
        
        # Área de mensagens com altura ajustável
        message_area_height = 500
        with st.container(height=message_area_height):
            # Estilizar o início da conversa com informações do modelo
            if not st.session_state.chat_history:
                # Container centralizado para exibir informações do modelo
                col1, col2, col3 = st.columns([1, 3, 1])
                with col2:
                    st.markdown(f"""
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; text-align: center;">
                        <div style="font-size: 4rem; margin-bottom: 1rem;">
                            {self._get_model_icon(current_model)}
                        </div>
                        <h2 style="margin-bottom: 0.5rem;">{current_model}</h2>
                        <p style="color: #888; margin-bottom: 2rem;">{self._get_model_description(current_model)}</p>
                        <p>Como posso ajudar você hoje?</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Exibir mensagens existentes
                for message in st.session_state.chat_history:
                    self.render_message(message)
        
        # Container de entrada fixo na parte inferior
        with st.container(border=True):
            # Área de ações adicionais (anexar documentos, etc)
            col1, col2, col3, col4 = st.columns([1, 1, 7, 1])
            with col1:
                st.button("📎", help="Anexar arquivo", key="attach_file")
            with col2:
                st.button("🎤", help="Entrada de voz", key="voice_input")
            with col4:
                # Botão de limpar conversa
                if st.button("🧹", help="Limpar conversa"):
                    self.create_new_session()
                    st.rerun()
            
            # Área de entrada de texto
            user_input = st.text_area(
                "Envie uma mensagem...",
                height=80,
                placeholder=f"Mensagem para {current_model}...",
                label_visibility="collapsed",
                key="chat_input"
            )
            
            # Linha com botões adicionais e o botão de enviar
            col1, col2, col3, col4 = st.columns([6, 1, 1, 2])
            
            with col1:
                # Texto informativo sobre o modelo
                if current_model == "GPT-4o":
                    st.markdown("<small>GPT-4o da OpenAI • Responde com conhecimento até abril de 2024</small>", unsafe_allow_html=True)
                elif current_model == "Claude-3":
                    st.markdown("<small>Claude 3 da Anthropic • Responde com conhecimento até abril de 2024</small>", unsafe_allow_html=True)
                elif current_model == "Llama-3":
                    st.markdown("<small>Llama 3 da Meta • Open-source e rápido</small>", unsafe_allow_html=True)
                elif current_model == "Grok-2":
                    st.markdown("<small>Grok 2 da xAI • Responde com personalidade</small>", unsafe_allow_html=True)
            
            with col3:
                # Configurações rápidas
                st.button("⚙️", help="Configurações rápidas")
            
            with col4:
                # Botão de enviar com cor personalizada baseada no modelo
                if st.button("Enviar", type="primary", use_container_width=True) and user_input:
                    # Desabilitar a entrada durante o processamento
                    with st.spinner(f"{current_model} está pensando..."):
                        self.send_message(user_input)
                    st.rerun()
    
    def _get_model_icon(self, model_name):
        """Retorna o ícone apropriado para o modelo"""
        icons = {
            "GPT-4o": "🧠",
            "Claude-3": "🔮",
            "Llama-3": "🦙",
            "Grok-2": "⚡"
        }
        return icons.get(model_name, "🤖")
    
    def _get_model_description(self, model_name):
        """Retorna a descrição apropriada para o modelo"""
        descriptions = {
            "GPT-4o": "Modelo multimodal avançado da OpenAI",
            "Claude-3": "Assistente inteligente e seguro da Anthropic",
            "Llama-3": "Modelo open-source da Meta",
            "Grok-2": "Modelo conversacional da xAI"
        }
        return descriptions.get(model_name, "Assistente de IA")
