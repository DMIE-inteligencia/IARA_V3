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
    
    def render(self):
        """Render the document upload component"""
        st.header("Gerenciamento de Documentos")
        
        # Create tabs for upload and management
        tab1, tab2 = st.tabs(["Carregar Documentos", "Gerenciar Documentos"])
        
        with tab1:
            st.subheader("Carregar Novos Documentos")
            st.write("Carregue documentos para fazer perguntas sobre eles.")
            
            uploaded_files = st.file_uploader(
                "Escolha os arquivos para carregar",
                accept_multiple_files=True,
                type=["pdf", "docx", "txt", "csv", "md"]
            )
            
            description = st.text_area("Descrição do Documento (opcional)", height=100)
            
            if st.button("Processar Documentos") and uploaded_files:
                for file in uploaded_files:
                    self.upload_document(file, description)
                
                st.rerun()
        
        with tab2:
            st.subheader("Seus Documentos")
            
            # Get user documents
            documents = self.get_user_documents()
            
            if not documents:
                st.info("Você ainda não carregou nenhum documento.")
            else:
                for doc in documents:
                    with st.expander(f"{doc.get('filename')} ({doc.get('file_type')})"):
                        st.write(f"**ID:** {doc.get('document_id')}")
                        st.write(f"**Tamanho:** {doc.get('size_bytes', 0) / 1024:.2f} KB")
                        st.write(f"**Carregado em:** {doc.get('upload_timestamp')}")
                        st.write(f"**Páginas:** {doc.get('num_pages', 'N/A')}")
                        st.write(f"**Fragmentos:** {doc.get('num_chunks', 'N/A')}")
                        
                        if doc.get('description'):
                            st.write(f"**Descrição:** {doc.get('description')}")
                        
                        if st.button("Excluir Documento", key=f"delete_{doc.get('document_id')}"):
                            if self.delete_document(doc.get('document_id')):
                                st.success("Documento excluído com sucesso")
                                st.rerun()
                            else:
                                st.error("Falha ao excluir documento")
