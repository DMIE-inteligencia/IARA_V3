import os
import logging
from typing import List, Dict, Any
import numpy as np

# In a real implementation, we would use a proper embedding model like OpenAI's ada-002,
# a HuggingFace model, or similar. For this demo, we'll use a simplified approach.

class EmbeddingGenerator:
    """
    Generates embeddings for document chunks using external embedding models.
    """
    
    def __init__(self, model_name: str = "openai"):
        """Initialize the embedding generator"""
        self.logger = logging.getLogger("embeddings")
        self.model_name = model_name
        
        # Check if OpenAI API key is available
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if self.model_name == "openai" and not self.openai_api_key:
            self.logger.warning("No OpenAI API key found. Using mock embeddings.")
            self.use_mock = True
        else:
            self.use_mock = False
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if self.use_mock or self.model_name == "mock":
            return self._generate_mock_embeddings(texts)
        elif self.model_name == "openai":
            return self._generate_openai_embeddings(texts)
        else:
            self.logger.warning(f"Unknown embedding model: {self.model_name}. Using mock embeddings.")
            return self._generate_mock_embeddings(texts)
    
    def _generate_mock_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate deterministic mock embeddings for demonstration purposes"""
        embeddings = []
        for text in texts:
            # Create a deterministic embedding based on the text content
            seed = sum(ord(c) for c in text)
            np.random.seed(seed)
            
            # Generate a 1536-dimensional vector (same as OpenAI's ada-002)
            embedding = np.random.normal(0, 1, 1536).tolist()
            
            # Normalize the embedding
            magnitude = sum(x**2 for x in embedding) ** 0.5
            normalized = [x / magnitude for x in embedding]
            
            embeddings.append(normalized)
        return embeddings
    
    def _generate_openai_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's embedding API"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            # Process in batches to avoid token limits
            all_embeddings = []
            
            # OpenAI recommends batches of ~2048 tokens
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = client.embeddings.create(
                    input=batch,
                    model="text-embedding-3-small"
                )
                
                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating OpenAI embeddings: {str(e)}")
            # Fall back to mock embeddings
            return self._generate_mock_embeddings(texts)
