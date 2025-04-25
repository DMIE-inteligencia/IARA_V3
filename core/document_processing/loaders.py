import os
import logging
from typing import Dict, Any, Optional

class DocumentLoader:
    """
    Loads and processes documents from various file formats.
    """
    
    def __init__(self):
        """Initialize the document loader"""
        self.logger = logging.getLogger("document_loader")
        self.supported_formats = {
            ".txt": self._load_text,
            ".md": self._load_text,
            ".csv": self._load_text,
            ".pdf": self._load_pdf,
            ".docx": self._load_docx
        }
    
    def load_document(self, file_path: str) -> str:
        """Load a document from the specified file path"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get file extension
        _, extension = os.path.splitext(file_path.lower())
        
        # Check if file format is supported
        if extension not in self.supported_formats:
            supported = ", ".join(self.supported_formats.keys())
            raise ValueError(f"Unsupported file format: {extension}. Supported formats: {supported}")
        
        # Load document using the appropriate loader
        loader = self.supported_formats[extension]
        return loader(file_path)
    
    def _load_text(self, file_path: str) -> str:
        """Load a plain text document"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()
    
    def _load_pdf(self, file_path: str) -> str:
        """Load a PDF document"""
        try:
            # For a real implementation, we would use PyPDF2, pdfminer, etc.
            # For this demo, we'll assume it's a text-based PDF and try to read it as text
            self.logger.warning("PDF support is limited in this demo. Using plain text loader.")
            return self._load_text(file_path)
        except Exception as e:
            self.logger.error(f"Error loading PDF: {str(e)}")
            raise ValueError(f"Error loading PDF: {str(e)}")
    
    def _load_docx(self, file_path: str) -> str:
        """Load a Word document"""
        try:
            # For a real implementation, we would use python-docx
            # For this demo, we'll assume it's a text-based document and try to read it as text
            self.logger.warning("DOCX support is limited in this demo. Using plain text loader.")
            return self._load_text(file_path)
        except Exception as e:
            self.logger.error(f"Error loading DOCX: {str(e)}")
            raise ValueError(f"Error loading DOCX: {str(e)}")
