import os
import logging
from typing import Dict, List, Optional, Any

from core.models.llm import LLMProvider
from core.models.base import ModelResponse


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI language models"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the OpenAI provider"""
        self.logger = logging.getLogger("openai_provider")
        
        # Use provided API key or get from environment
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            self.logger.warning("No OpenAI API key provided. API calls will fail.")
        
        # Map of OpenAI model IDs to their max tokens
        self.model_context_lengths = {
            "gpt-4o": 128000,  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
            "gpt-4-turbo": 128000,
            "gpt-4": 8192,
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385
        }
    
    def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
    ) -> ModelResponse:
        """Generate text using OpenAI API"""
        try:
            from openai import OpenAI
            
            # Initialize client
            client = OpenAI(api_key=self.api_key)
            
            # Calculate max tokens if not provided
            if not max_tokens:
                # Estimate prompt tokens (rough approximation)
                prompt_tokens = len(prompt) // 4
                
                # Get context length for the model
                context_length = self.model_context_lengths.get(model, 4096)
                
                # Set max tokens to a portion of available space
                max_tokens = min(4000, context_length - prompt_tokens - 100)
            
            # Prepare request parameters
            params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add optional parameters if provided
            if stop_sequences:
                params["stop"] = stop_sequences
            if top_p is not None:
                params["top_p"] = top_p
            if frequency_penalty is not None:
                params["frequency_penalty"] = frequency_penalty
            if presence_penalty is not None:
                params["presence_penalty"] = presence_penalty
            
            # Make API request
            response = client.chat.completions.create(**params)
            
            # Extract and return response
            return ModelResponse(
                text=response.choices[0].message.content,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                model=model,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Exception as e:
            self.logger.error(f"Error generating text with OpenAI: {str(e)}")
            # Return error message
            return ModelResponse(
                text=f"Error generating response: {str(e)}",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                model=model,
                finish_reason="error"
            )
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        """List available OpenAI models"""
        # For simplicity, return hardcoded list
        return [
            {
                "id": "gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                "name": "GPT-4o",
                "context_length": 128000,
                "description": "OpenAI's most advanced model, optimized for both vision and language tasks."
            },
            {
                "id": "gpt-4-turbo",
                "name": "GPT-4 Turbo",
                "context_length": 128000,
                "description": "Fast and cost-effective version of GPT-4 with large context window."
            },
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "context_length": 8192,
                "description": "OpenAI's most advanced model."
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "context_length": 16385,
                "description": "Fast and cost-effective model with good general capabilities."
            }
        ]
