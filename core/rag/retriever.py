import logging
from typing import Dict, List, Any, Optional
import numpy as np
from collections import defaultdict

from schema import DocumentChunk


class VectorRetriever:
    """
    Manages vector storage and retrieval of document chunks.
    """
    
    def __init__(self):
        """Initialize the vector retriever"""
        self.logger = logging.getLogger("vector_retriever")
        
        # In-memory store for document chunks
        self.documents: Dict[str, List[DocumentChunk]] = defaultdict(list)
        
        # In-memory vector store (document_id -> chunk_id -> embedding)
        self.vectors: Dict[str, Dict[str, List[float]]] = defaultdict(dict)
        
        # Initialize embeddings generator
        from core.document_processing.embeddings import EmbeddingGenerator
        self.embedding_generator = EmbeddingGenerator()
    
    def add_documents(self, chunks: List[DocumentChunk]):
        """Add document chunks to the vector store"""
        # Group chunks by document_id
        doc_chunks = defaultdict(list)
        for chunk in chunks:
            doc_chunks[chunk.document_id].append(chunk)
        
        # Process each document's chunks
        for doc_id, doc_chunks_list in doc_chunks.items():
            # Store chunks
            self.documents[doc_id].extend(doc_chunks_list)
            
            # Store vectors
            for chunk in doc_chunks_list:
                if chunk.embedding:
                    self.vectors[doc_id][chunk.chunk_id] = chunk.embedding
                else:
                    self.logger.warning(f"Chunk {chunk.chunk_id} has no embedding")
    
    def remove_document(self, document_id: str) -> int:
        """Remove a document and its chunks from the vector store"""
        # Get number of chunks to be removed
        num_chunks = len(self.documents.get(document_id, []))
        
        # Remove document chunks
        if document_id in self.documents:
            del self.documents[document_id]
        
        # Remove vectors
        if document_id in self.vectors:
            del self.vectors[document_id]
        
        return num_chunks
    
    def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query
        
        Parameters:
        - query: The search query
        - filters: Dictionary of filters to apply (e.g., document_id, user_id)
        - k: Number of results to return
        
        Returns:
        - List of retrieval results with document chunks and metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_generator.generate_embeddings([query])[0]
        
        # Get document IDs to search based on filters
        document_ids = self._filter_document_ids(filters)
        
        if not document_ids:
            return []
        
        # Calculate similarity scores for all chunks
        all_results = []
        
        for doc_id in document_ids:
            doc_vectors = self.vectors.get(doc_id, {})
            doc_chunks = {chunk.chunk_id: chunk for chunk in self.documents.get(doc_id, [])}
            
            for chunk_id, embedding in doc_vectors.items():
                chunk = doc_chunks.get(chunk_id)
                if not chunk:
                    continue
                
                # Calculate cosine similarity
                score = self._cosine_similarity(query_embedding, embedding)
                
                # Create result entry
                all_results.append({
                    "document_id": doc_id,
                    "chunk_id": chunk_id,
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "score": score
                })
        
        # Sort by score
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top k results
        return all_results[:k]
    
    def _filter_document_ids(self, filters: Optional[Dict[str, Any]] = None) -> List[str]:
        """Filter document IDs based on filter criteria"""
        if not filters:
            # Return all document IDs if no filters
            return list(self.documents.keys())
        
        # Check for document_id filter
        if "document_id" in filters:
            doc_ids = filters["document_id"]
            
            # Convert to list if single value
            if not isinstance(doc_ids, list):
                doc_ids = [doc_ids]
            
            # Ensure all IDs exist
            return [doc_id for doc_id in doc_ids if doc_id in self.documents]
        
        # For more complex filtering, we'd check other metadata fields
        # This implementation is simplified
        return list(self.documents.keys())
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        # Convert to numpy arrays
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        # Calculate dot product
        dot_product = np.dot(vec1_np, vec2_np)
        
        # Calculate magnitudes
        magnitude1 = np.linalg.norm(vec1_np)
        magnitude2 = np.linalg.norm(vec2_np)
        
        # Calculate cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
