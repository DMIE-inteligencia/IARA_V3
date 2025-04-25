import streamlit as st
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from schema import DocumentMetadata, MessageType, AgentType, MessagePriority, Message
from core.agents.agent_factory import AgentFactory


class DocumentUpload:
    def __init__(self):
        """Initialize the document upload component"""
        self.orchestrator = st.session_state.agent_factory.get_agent(AgentType.ORCHESTRATOR)
        self.doc_processing_agent = st.session_state.agent_factory.get_agent(AgentType.DOCUMENT_PROCESSING)
    
    def upload_document(self, file, description: Optional[str] = None):
        """Handle document upload and processing"""
        try:
            # Create unique document ID
            document_id = f"doc_{uuid.uuid4()}"
            
            # Save the file temporarily
            file_path = f"/tmp/{file.name}"
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            
            # Prepare document metadata
            metadata = DocumentMetadata(
                filename=file.name,
                file_type=file.type,
                user_id=st.session_state.user_id,
                size_bytes=file.size,
                description=description,
                document_id=document_id
            )
            
            # Create message for document processing agent
            message = Message(
                sender=AgentType.ORCHESTRATOR,
                receiver=AgentType.DOCUMENT_PROCESSING,
                message_type=MessageType.COMMAND,
                priority=MessagePriority.MEDIUM,
                content={
                    "action": "process_document",
                    "file_path": file_path,
                    "metadata": metadata.dict()
                }
            )
            
            # Send message and wait for response
            with st.spinner("Processando documento..."):
                response = self.orchestrator.send_message_and_wait(message)
            
            # Check response and update UI
            if response and response.message_type != MessageType.ERROR:
                # Add document to session state
                st.session_state.documents.append(document_id)
                
                # Update document metadata with processed info
                processed_metadata = response.content.get("metadata", {})
                metadata.num_pages = processed_metadata.get("num_pages")
                metadata.num_chunks = processed_metadata.get("num_chunks")
                
                st.success(f"Documento '{file.name}' carregado e processado com sucesso!")
                return metadata
            else:
                error_msg = response.content.get("error", "Erro desconhecido") if response else "Sem resposta do agente"
                st.error(f"Falha ao processar documento: {error_msg}")
                return None
                
        except Exception as e:
            st.error(f"Erro ao carregar documento: {str(e)}")
            return None
        finally:
            # Clean up temporary file
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
    
    def get_user_documents(self):
        """Retrieve documents for the current user"""
        message = Message(
            sender=AgentType.ORCHESTRATOR,
            receiver=AgentType.DOCUMENT_PROCESSING,
            message_type=MessageType.COMMAND,
            content={
                "action": "get_user_documents",
                "user_id": st.session_state.user_id
            }
        )
        
        response = self.orchestrator.send_message_and_wait(message)
        
        if response and response.message_type != MessageType.ERROR:
            return response.content.get("documents", [])
        else:
            st.error("Falha ao recuperar documentos")
            return []
    
    def delete_document(self, document_id: str):
        """Delete a document"""
        message = Message(
            sender=AgentType.ORCHESTRATOR,
            receiver=AgentType.DOCUMENT_PROCESSING,
            message_type=MessageType.COMMAND,
            content={
                "action": "delete_document",
                "document_id": document_id,
                "user_id": st.session_state.user_id
            }
        )
        
        response = self.orchestrator.send_message_and_wait(message)
        
        if response and response.message_type != MessageType.ERROR:
            # Remove from session state
            if document_id in st.session_state.documents:
                st.session_state.documents.remove(document_id)
            return True
        else:
            return False
    
    def _get_file_icon(self, file_type: str) -> str:
        """Return an appropriate icon for the file type"""
        if "pdf" in file_type.lower():
            return "📄"
        elif "word" in file_type.lower() or "docx" in file_type.lower():
            return "📝"
        elif "text" in file_type.lower() or "txt" in file_type.lower():
            return "📃"
        elif "csv" in file_type.lower() or "excel" in file_type.lower() or "xlsx" in file_type.lower():
            return "📊"
        else:
            return "📑"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def render(self):
        """Render the document upload component with modern styling"""
        # Área principal
        st.container(height=10)  # Espaçamento superior
        
        # Cards de navegação
        tabs = st.tabs(["📤 Upload", "📚 Biblioteca", "🔍 Análise"])
        
        # Tab de Upload
        with tabs[0]:
            with st.container(border=False):
                # Título e descrição
                st.markdown("""
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2>Upload de Documentos</h2>
                    <p style="color: #666;">Adicione documentos para análise e obtenha insights da IA</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Área de upload com estilo visual
                with st.container(border=True):
                    col1, col2 = st.columns([2, 3])
                    
                    with col1:
                        st.markdown("""
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 4rem; margin-bottom: 1rem;">
                                📄➡️🧠
                            </div>
                            <p>Formatos suportados:</p>
                            <p style="color: #666; font-size: 0.9rem;">
                                PDF, DOCX, TXT, CSV, MD
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown("### Selecione arquivos para upload")
                        uploaded_files = st.file_uploader(
                            "Arraste e solte os arquivos aqui",
                            accept_multiple_files=True,
                            type=["pdf", "docx", "txt", "csv", "md"],
                            label_visibility="collapsed"
                        )
                        
                        if uploaded_files:
                            st.markdown(f"**{len(uploaded_files)} arquivo(s) selecionado(s)**")
                            
                            # Opções adicionais
                            with st.expander("Opções de processamento", expanded=True):
                                description = st.text_area(
                                    "Adicione uma descrição ou tags (opcional)",
                                    placeholder="Exemplo: Relatório financeiro Q1 2025, documentação técnica, etc.",
                                    height=80
                                )
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.checkbox("Extrair texto", value=True, help="Extrair todo o texto para pesquisa")
                                with col_b:
                                    st.checkbox("Gerar embeddings", value=True, help="Criar vetores para pesquisa semântica")
                            
                            # Botão de processamento
                            if st.button("Processar Documentos", type="primary", use_container_width=True):
                                with st.status("Processando documentos...") as status:
                                    for i, file in enumerate(uploaded_files):
                                        st.write(f"Processando {file.name}...")
                                        self.upload_document(file, description)
                                    status.update(label="Processamento concluído!", state="complete")
                                st.rerun()
        
        # Tab de Biblioteca
        with tabs[1]:
            # Obter documentos do usuário
            documents = self.get_user_documents()
            
            if not documents:
                # Estado vazio estilizado
                st.markdown("""
                <div style="text-align: center; padding: 50px 0;">
                    <div style="font-size: 4rem; margin-bottom: 1rem;">
                        📚
                    </div>
                    <h3>Sua biblioteca está vazia</h3>
                    <p style="color: #666;">Carregue documentos na aba de Upload para começar</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Título com contador
                st.markdown(f"### Sua Biblioteca ({len(documents)} documentos)")
                
                # Campo de busca
                st.text_input("Buscar documentos", placeholder="Digite para filtrar...", key="doc_search")
                
                # Área de filtros
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.selectbox("Ordenar por", ["Data (mais recente)", "Data (mais antigo)", "Nome (A-Z)", "Nome (Z-A)"])
                with col2:
                    st.multiselect("Tipo de arquivo", ["PDF", "DOCX", "TXT", "CSV"])
                with col3:
                    st.number_input("Tamanho mínimo (KB)", min_value=0, value=0)
                
                # Grade de documentos
                st.markdown("---")
                
                # Usar colunas para criar uma grade visual
                cols = st.columns(3)
                for i, doc in enumerate(documents):
                    col_idx = i % 3
                    with cols[col_idx]:
                        with st.container(border=True):
                            # Cabeçalho do card
                            file_icon = self._get_file_icon(doc.get('file_type', ''))
                            file_name = doc.get('filename', 'Documento sem nome')
                            upload_date = doc.get('upload_timestamp', datetime.now())
                            
                            if isinstance(upload_date, str):
                                try:
                                    upload_date = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                                except:
                                    upload_date = datetime.now()
                            
                            # Formatação da data
                            date_str = upload_date.strftime("%d/%m/%Y")
                            
                            st.markdown(f"""
                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                <div style="font-size: 2rem; margin-right: 10px;">{file_icon}</div>
                                <div>
                                    <div style="font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{file_name}</div>
                                    <div style="color: #888; font-size: 0.8rem;">Adicionado em {date_str}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Estatísticas do documento
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Páginas:** {doc.get('num_pages', 'N/A')}")
                            with col_b:
                                st.markdown(f"**Tamanho:** {self._format_file_size(doc.get('size_bytes', 0))}")
                            
                            # Descrição se existir
                            if doc.get('description'):
                                with st.expander("Descrição", expanded=False):
                                    st.write(doc.get('description'))
                            
                            # Ações do documento
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.button("🔍 Visualizar", key=f"view_{doc.get('document_id')}", use_container_width=True)
                            with col_b:
                                delete_btn = st.button("🗑️ Excluir", key=f"delete_{doc.get('document_id')}", use_container_width=True)
                                if delete_btn:
                                    if self.delete_document(doc.get('document_id')):
                                        st.success("Documento excluído")
                                        st.rerun()
                                    else:
                                        st.error("Erro ao excluir")
        
        # Tab de Análise
        with tabs[2]:
            st.markdown("""
            <div style="text-align: center; padding: 20px 0;">
                <h2>Análise de Documentos</h2>
                <p style="color: #666;">Obtenha insights e visualizações dos seus documentos</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Exemplo de visualizações (placeholders)
            with st.container(border=True):
                st.markdown("### Estatísticas da Biblioteca")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total de Documentos", len(documents))
                with col2:
                    st.metric("Páginas Indexadas", sum(doc.get('num_pages', 0) for doc in documents if doc.get('num_pages')))
                with col3:
                    total_size = sum(doc.get('size_bytes', 0) for doc in documents)
                    st.metric("Tamanho Total", self._format_file_size(total_size))
                with col4:
                    st.metric("Fragmentos", sum(doc.get('num_chunks', 0) for doc in documents if doc.get('num_chunks')))
                
                # Gráfico de exemplo
                st.markdown("### Distribuição por Tipo de Arquivo")
                st.info("Os gráficos e visualizações avançadas estarão disponíveis em breve.")