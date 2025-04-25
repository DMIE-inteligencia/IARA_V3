import os
import sys
import streamlit as st
from datetime import datetime

# Add the root directory to the Python path to enable proper imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.components.chat_interface_new import ChatInterface
from app.components.document_upload_new import DocumentUpload
from app.components.user_chat_interface import UserChatInterface
from infrastructure.state.state_manager import StateManager
from core.agents.agent_factory import AgentFactory


def init_session_state():
    """Initialize session state variables if they don't exist"""
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "documents" not in st.session_state:
        st.session_state.documents = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "agents_initialized" not in st.session_state:
        st.session_state.agents_initialized = False


def initialize_agents():
    """Initialize the agent system"""
    if not st.session_state.agents_initialized:
        # Create the agent factory
        factory = AgentFactory()
        
        # Initialize the state manager
        state_manager = StateManager()
        
        # Store in session state
        st.session_state.agent_factory = factory
        st.session_state.state_manager = state_manager
        
        # Create all agents
        factory.create_all_agents()
        
        # Start the orchestrator
        orchestrator = factory.get_agent("orchestrator")
        orchestrator.start()
        
        st.session_state.agents_initialized = True


def login_page():
    """Display the login page"""
    # Use columns to center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Logo and title with modern styling
        st.markdown("""
            <div style="text-align: center; padding: 2rem 0;">
                <h1 style="font-size: 3rem; font-weight: 700; margin-bottom: 0;">IARA</h1>
                <p style="font-size: 1.2rem; color: #666; margin-top: 0;">Inteligência Artificial para Recuperação e Análise</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Login form with card-like appearance
        with st.container(border=True):
            st.markdown("### Login")
            username = st.text_input("Nome de Usuário", placeholder="Digite seu nome de usuário")
            password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            
            # Remember me checkbox and login button
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.checkbox("Lembrar de mim", value=False)
            with col_b:
                st.markdown("<div style='text-align: right;'>Esqueceu a senha?</div>", unsafe_allow_html=True)
            
            login_button = st.button("Entrar", type="primary", use_container_width=True)
            
            if login_button:
                # Verificação de login com diferenciação de usuário e administrador
                if username == "admin" and password == "password":
                    # Login como administrador
                    st.session_state.user_id = "admin_123"
                    st.session_state.user_type = "admin"
                    st.session_state.authenticated = True
                    st.rerun()
                elif username == "usuario" and password == "password":
                    # Login como usuário comum
                    st.session_state.user_id = "user_456"
                    st.session_state.user_type = "user"
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Nome de usuário ou senha inválidos")
                    
                    # Dica sobre as credenciais disponíveis (apenas para demonstração)
                    with st.expander("Contas disponíveis para demonstração"):
                        st.markdown("""
                        **Administrador:**
                        - Usuário: `admin`
                        - Senha: `password`
                        
                        **Usuário Normal:**
                        - Usuário: `usuario`
                        - Senha: `password`
                        """)
        
        # Registration section
        st.markdown("<div style='text-align: center; margin-top: 1rem;'>Não tem uma conta?</div>", unsafe_allow_html=True)
        if st.button("Criar nova conta", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()
            
        # Show registration form if button was clicked
        if st.session_state.get("show_register", False):
            with st.container(border=True):
                st.markdown("### Cadastro de Novo Usuário")
                new_username = st.text_input("Novo Nome de Usuário", placeholder="Escolha um nome de usuário")
                new_email = st.text_input("Email", placeholder="Digite seu email")
                new_password = st.text_input("Nova Senha", type="password", placeholder="Escolha uma senha segura")
                confirm_password = st.text_input("Confirmar Senha", type="password", placeholder="Digite a senha novamente")
                
                register_button = st.button("Cadastrar", type="primary", use_container_width=True)
                
                if register_button:
                    if new_password != confirm_password:
                        st.error("As senhas não coincidem")
                    elif not new_username or not new_password:
                        st.error("Nome de usuário e senha são obrigatórios")
                    else:
                        # In a real implementation, this would register the user with the security agent
                        st.success("Usuário cadastrado com sucesso! Você pode fazer login agora.")
                        st.session_state.show_register = False


def main_app():
    """Display the main application after login"""
    # Inicializar variáveis de sessão para o modelo e histórico de chats
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "GPT-4o"
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = [
            {"id": "session_1", "title": "Nova conversa", "active": True, "created_at": datetime.now()}
        ]
    if "active_page" not in st.session_state:
        st.session_state.active_page = "Chat"
    
    # Sidebar moderna com opções de navegação
    with st.sidebar:
        # Logo e informações do usuário
        st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="font-size: 2.2rem; margin-bottom: 0;">IARA</h1>
                <p style="font-size: 0.9rem; color: #888; margin-top: 0;">Assistente IA v3.0</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Perfil do usuário
        with st.container(border=False, height=70):
            col1, col2 = st.columns([1, 4])
            with col1:
                st.markdown("👤")  # Avatar do usuário
            with col2:
                st.markdown(f"**Usuário:** {st.session_state.user_id.replace('user_', '')}")
                st.markdown("Plano Premium", help="Seu plano de assinatura")
        
        st.markdown("---")
        
        # Botão de nova conversa
        if st.button("+ Nova Conversa", use_container_width=True, type="primary"):
            new_session_id = f"session_{len(st.session_state.chat_sessions) + 1}"
            # Marcar todas as sessões como inativas
            for session in st.session_state.chat_sessions:
                session["active"] = False
            # Adicionar nova sessão
            st.session_state.chat_sessions.append({
                "id": new_session_id, 
                "title": "Nova conversa", 
                "active": True,
                "created_at": datetime.now()
            })
            st.session_state.current_session_id = new_session_id
            st.session_state.chat_history = []
            st.rerun()
        
        # Lista de conversas recentes
        st.markdown("### Conversas Recentes")
        for idx, session in enumerate(st.session_state.chat_sessions):
            session_title = session["title"]
            is_active = session["active"]
            
            # Estilo diferente para sessão ativa
            if is_active:
                # Sessão ativa com fundo destacado
                with st.container(border=True, height=50):
                    col1, col2, col3 = st.columns([7, 1, 1])
                    with col1:
                        st.markdown(f"**{session_title}**")
                    with col2:
                        if st.button("✏️", key=f"edit_{idx}", help="Editar título"):
                            st.session_state.editing_session = idx
                    with col3:
                        if st.button("🗑️", key=f"delete_{idx}", help="Excluir conversa"):
                            st.session_state.chat_sessions.pop(idx)
                            if len(st.session_state.chat_sessions) > 0:
                                st.session_state.chat_sessions[0]["active"] = True
                            else:
                                st.session_state.chat_sessions.append({
                                    "id": "session_new", 
                                    "title": "Nova conversa", 
                                    "active": True,
                                    "created_at": datetime.now()
                                })
                            st.rerun()
            else:
                # Sessão inativa
                if st.button(session_title, key=f"session_{idx}", use_container_width=True):
                    # Ativar esta sessão e desativar as outras
                    for s in st.session_state.chat_sessions:
                        s["active"] = False
                    st.session_state.chat_sessions[idx]["active"] = True
                    st.session_state.current_session_id = session["id"]
                    st.rerun()
        
        st.markdown("---")
        
        # Navegação principal
        st.markdown("### Menu")
        nav_options = ["Chat", "Documentos", "Configurações"]
        for nav in nav_options:
            if st.button(nav, use_container_width=True, 
                         type="primary" if st.session_state.active_page == nav else "secondary"):
                st.session_state.active_page = nav
                st.rerun()
            
        # Modelos disponíveis
        st.markdown("### Escolha o Modelo")
        
        # Cards de seleção de modelo
        model_options = [
            {"id": "GPT-4o", "name": "GPT-4o", "company": "OpenAI", "icon": "🧠", "desc": "Modelo poderoso para tarefas complexas"},
            {"id": "Claude-3", "name": "Claude 3", "company": "Anthropic", "icon": "🔮", "desc": "Especialista em raciocínio e análise"},
            {"id": "Llama-3", "name": "Llama 3", "company": "Meta", "icon": "🦙", "desc": "Open-source e rápido"},
            {"id": "Grok-2", "name": "Grok 2", "company": "xAI", "icon": "⚡", "desc": "Inteligente e criativo"}
        ]
        
        for model in model_options:
            # Destacar o modelo selecionado
            if st.session_state.selected_model == model["id"]:
                with st.container(border=True):
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        st.markdown(f"<div style='font-size:2rem;'>{model['icon']}</div>", unsafe_allow_html=True)
                    with col2:
                        st.markdown(f"**{model['name']}**")
                        st.markdown(f"<small>{model['company']}</small>", unsafe_allow_html=True)
            else:
                if st.button(f"{model['icon']} {model['name']}", key=f"model_{model['id']}", use_container_width=True):
                    st.session_state.selected_model = model["id"]
                    st.rerun()
        
        st.markdown("---")
        
        # Logout button no rodapé
        if st.button("Sair da conta", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.authenticated = False
            st.rerun()
    
    # Área principal de conteúdo
    if st.session_state.active_page == "Chat":
        chat_interface = ChatInterface()
        chat_interface.render()
    
    elif st.session_state.active_page == "Documentos":
        document_upload = DocumentUpload()
        document_upload.render()
    
    elif st.session_state.active_page == "Configurações":
        # Interface moderna de configurações
        st.markdown("## Configurações")
        
        # Tabs para organizar as configurações
        tab1, tab2, tab3 = st.tabs(["Perfil", "Preferências", "Avançado"])
        
        with tab1:
            # Configurações de perfil
            st.markdown("### Seu Perfil")
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown("### 👤")
                with col2:
                    st.text_input("Nome Completo", placeholder="Seu nome")
                    st.text_input("Endereço de Email", placeholder="seu.email@exemplo.com")
                    st.text_input("Empresa", placeholder="Nome da sua organização")
                
                st.divider()
                st.subheader("Alterar Senha")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input("Senha Atual", type="password")
                with col2:
                    st.text_input("Nova Senha", type="password")
                
                if st.button("Salvar Alterações", type="primary", use_container_width=True):
                    st.success("Perfil atualizado com sucesso!")
        
        with tab2:
            # Preferências de usuário
            st.markdown("### Preferências")
            
            with st.container(border=True):
                st.markdown("#### Aparência")
                st.toggle("Modo Escuro", value=False)
                st.toggle("Mostrar ícones grandes", value=True)
                
                st.markdown("#### Notificações")
                st.toggle("Email de novidades", value=True)
                st.toggle("Alertas do sistema", value=True)
                
                st.markdown("#### Idioma")
                st.selectbox("Idioma da Interface", options=["Português (Brasil)", "English", "Español"])
                
                if st.button("Aplicar Preferências", type="primary", use_container_width=True):
                    st.success("Preferências salvas!")
        
        with tab3:
            # Configurações avançadas
            st.markdown("### Configurações Avançadas")
            
            with st.container(border=True):
                st.markdown("#### Parâmetros do Modelo")
                st.slider("Temperatura", min_value=0.0, max_value=1.0, value=0.7, step=0.1,
                         help="Controla a aleatoriedade das respostas")
                st.slider("Top P", min_value=0.0, max_value=1.0, value=0.9, step=0.1,
                         help="Controla a diversidade das respostas")
                st.number_input("Máximo de Tokens", min_value=100, max_value=8000, value=2000, step=100,
                               help="Limite máximo de tokens na resposta")
                
                st.markdown("#### Parâmetros de Recuperação")
                st.slider("Número de fragmentos", min_value=1, max_value=10, value=4, step=1,
                         help="Quantidade de fragmentos de documentos a recuperar")
                st.slider("Limiar de similaridade", min_value=0.0, max_value=1.0, value=0.75, step=0.05,
                         help="Limiar mínimo de similaridade para recuperação de documentos")
                
                if st.button("Aplicar Configurações", type="primary", use_container_width=True):
                    st.success("Configurações avançadas aplicadas!")


def user_app():
    """Interface simplificada para usuários comuns"""
    # Cabeçalho e configuração de página
    st.set_page_config(
        page_title="IARA - Assistente de IA",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializar dados da sessão
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Renderizar a interface simplificada de chat
    user_interface = UserChatInterface()
    user_interface.render()


def main():
    """Main application entry point"""
    # Verificar se a página já foi configurada
    if "page_configured" not in st.session_state:
        # Set page configuration
        st.set_page_config(
            page_title="IARA - Assistente de Documentos",
            page_icon="📚",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        st.session_state.page_configured = True
    
    # Initialize session state
    init_session_state()
    
    # Initialize agents
    initialize_agents()
    
    # Display the appropriate page based on authentication state
    if st.session_state.authenticated:
        # Verificar tipo de usuário e mostrar interface apropriada
        if st.session_state.get("user_type") == "admin":
            # Interface completa para administradores
            main_app()
        else:
            # Interface simplificada para usuários comuns
            user_interface = UserChatInterface()
            user_interface.render()
    else:
        login_page()


if __name__ == "__main__":
    main()
