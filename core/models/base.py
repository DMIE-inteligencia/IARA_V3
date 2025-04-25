from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ModelResponse:
    """Standard response from a language model"""
    text: str
    usage: Dict[str, int]
    model: str
    finish_reason: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class BaseModelProvider(ABC):
    """Base class for all model providers"""
    
    @abstractmethod
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
        """Generate text using the language model"""
        pass
    
    @abstractmethod
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List available models from this provider"""
        pass
