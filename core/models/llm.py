from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Protocol

from core.models.base import ModelResponse, BaseModelProvider


class LLMProvider(BaseModelProvider):
    """Interface for LLM providers"""
    pass


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing"""
    
    def generate_text(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
    ) -> ModelResponse:
        """Generate mock text response"""
        # Simple mock response that includes part of the prompt
        response_text = f"This is a mock response to: '{prompt[:50]}...'"
        
        return ModelResponse(
            text=response_text,
            usage={"prompt_tokens": len(prompt), "completion_tokens": len(response_text), "total_tokens": len(prompt) + len(response_text)},
            model=model,
            finish_reason="stop"
        )
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List mock available models"""
        return [
            {"id": "mock-model-1", "name": "Mock Model 1", "context_length": 4096},
            {"id": "mock-model-2", "name": "Mock Model 2", "context_length": 8192}
        ]
