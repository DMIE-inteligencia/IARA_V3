import logging
import os
from typing import Dict, Any, Optional, List

from schema import AgentType, Message, MessageType
from core.agents.base_agent import BaseAgent
from core.models.llm import LLMProvider
from core.models.openai_models import OpenAIProvider
from infrastructure.messaging.message_broker import MessageBroker


class LLMAgent(BaseAgent):
    """
    The LLM agent is responsible for managing different language models
    and generating responses using the appropriate model.
    """
    
    def __init__(self, agent_type: AgentType, message_broker: MessageBroker, **kwargs):
        """Initialize the LLM agent"""
        super().__init__(agent_type, message_broker)
        self.logger = logging.getLogger("agent.llm")
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = "openai"
        
        # Initialize providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize LLM providers"""
        # Initialize OpenAI provider
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self.providers["openai"] = OpenAIProvider(api_key=openai_api_key)
        else:
            self.logger.warning("No OpenAI API key found. OpenAI provider not initialized.")
        
        # Initialize other providers as needed
        # For example: HuggingFace, Anthropic, etc.
    
    def handle_message(self, message: Message):
        """Handle messages sent to the LLM agent"""
        if message.message_type == MessageType.COMMAND:
            self._handle_command(message)
    
    def _handle_command(self, message: Message):
        """Handle command messages"""
        action = message.content.get("action")
        
        if action == "generate_text":
            self._handle_generate_text(message)
        elif action == "get_available_models":
            self._handle_get_available_models(message)
        else:
            self.send_error(
                message.sender,
                f"Unknown action: {action}",
                message.id
            )
    
    def _handle_generate_text(self, message: Message):
        """Handle text generation requests"""
        # Extract parameters
        prompt = message.content.get("prompt")
        if not prompt:
            self.send_error(message.sender, "Missing prompt parameter", message.id)
            return
        
        provider_name = message.content.get("provider", self.default_provider)
        model_name = message.content.get("model", "gpt-4o")  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
        
        # Optional parameters
        temperature = message.content.get("temperature", 0.7)
        max_tokens = message.content.get("max_tokens", 1000)
        
        # Advanced parameters (optional)
        stop_sequences = message.content.get("stop_sequences")
        top_p = message.content.get("top_p")
        frequency_penalty = message.content.get("frequency_penalty")
        presence_penalty = message.content.get("presence_penalty")
        
        # Get the provider
        provider = self.providers.get(provider_name)
        if not provider:
            self.send_error(
                message.sender,
                f"Provider {provider_name} not available",
                message.id
            )
            return
        
        try:
            # Generate text
            response = provider.generate_text(
                prompt=prompt,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                stop_sequences=stop_sequences,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty
            )
            
            # Send response
            self.send_response(
                message,
                {
                    "text": response.text,
                    "model": model_name,
                    "provider": provider_name,
                    "usage": response.usage,
                    "finish_reason": response.finish_reason
                }
            )
        except Exception as e:
            self.logger.error(f"Error generating text: {str(e)}")
            self.send_error(
                message.sender,
                f"Error generating text: {str(e)}",
                message.id
            )
    
    def _handle_get_available_models(self, message: Message):
        """Handle request for available models"""
        provider_name = message.content.get("provider")
        
        if provider_name:
            # Get models for specific provider
            provider = self.providers.get(provider_name)
            if not provider:
                self.send_error(
                    message.sender,
                    f"Provider {provider_name} not available",
                    message.id
                )
                return
            
            models = provider.list_available_models()
            self.send_response(message, {"provider": provider_name, "models": models})
        else:
            # Get models for all providers
            all_models = {}
            for name, provider in self.providers.items():
                all_models[name] = provider.list_available_models()
            
            self.send_response(message, {"providers": list(self.providers.keys()), "models": all_models})
