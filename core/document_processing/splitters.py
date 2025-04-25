import re
from typing import List, Optional, Dict, Any

class TextSplitter:
    """
    Splits documents into smaller chunks for processing and embedding.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize the text splitter with chunk parameters"""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks of specified size with overlap"""
        if not text:
            return []
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split by paragraph first
        paragraphs = self._split_into_paragraphs(text)
        
        # Merge paragraphs into chunks of appropriate size
        return self._merge_into_chunks(paragraphs)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        # Split on double newlines or paragraph markers
        pattern = r'\n\s*\n|\r\n\s*\r\n'
        paragraphs = re.split(pattern, text)
        
        # Remove empty paragraphs and strip whitespace
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _merge_into_chunks(self, paragraphs: List[str]) -> List[str]:
        """Merge paragraphs into chunks of appropriate size with overlap"""
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            # If adding this paragraph would exceed the chunk size and we already have content,
            # finalize the current chunk and start a new one
            if current_size + paragraph_size > self.chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Keep some paragraphs for overlap
                overlap_size = 0
                overlap_paragraphs = []
                
                # Add paragraphs from the end until we reach desired overlap
                for p in reversed(current_chunk):
                    if overlap_size + len(p) <= self.chunk_overlap:
                        overlap_paragraphs.insert(0, p)
                        overlap_size += len(p)
                    else:
                        break
                
                # Start new chunk with overlap paragraphs
                current_chunk = overlap_paragraphs
                current_size = overlap_size
            
            # Add paragraph to current chunk
            current_chunk.append(paragraph)
            current_size += paragraph_size
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def split_documents(self, documents: List[Dict[str, Any]], text_key: str = "text") -> List[Dict[str, Any]]:
        """Split documents into chunks, preserving metadata"""
        chunks = []
        
        for doc in documents:
            # Extract text and metadata
            text = doc.get(text_key, "")
            metadata = {k: v for k, v in doc.items() if k != text_key}
            
            # Split text
            text_chunks = self.split_text(text)
            
            # Create chunk documents with original metadata
            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    text_key: chunk_text,
                    "chunk_index": i,
                    **metadata
                })
        
        return chunks
