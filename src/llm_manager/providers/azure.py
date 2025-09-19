from openai import AzureOpenAI, AsyncAzureOpenAI
from .base import BaseProvider
import warnings
from typing import Dict, Any, Optional, Tuple

class AzureProvider(BaseProvider):
    """Provider for Azure OpenAI models"""
    
    def __init__(self, config):
        super().__init__(config)
        self.models = config.get("models", {})
        self._clients = {}  # Cache for sync clients
        self._async_clients = {}  # Cache for async clients
    
    def _create_cache_key(self, model_config: Dict[str, Any]) -> Tuple:
        """Create a cache key based on the model configuration"""
        return (
            model_config.get("api_key"),
            model_config.get("api_version"),
            model_config.get("azure_endpoint"),
            model_config.get("azure_deployment")
        )
    
    def _get_client(self, model_config: Dict[str, Any]) -> AzureOpenAI:
        """Get or create a synchronous Azure client for the given model config"""
        cache_key = self._create_cache_key(model_config)
        
        if cache_key not in self._clients:
            self._clients[cache_key] = AzureOpenAI(
                api_key=model_config.get("api_key"),
                api_version=model_config.get("api_version"),
                azure_endpoint=model_config.get("azure_endpoint"),
                azure_deployment=model_config.get("azure_deployment"),
            )
        
        return self._clients[cache_key]
    
    def _get_async_client(self, model_config: Dict[str, Any]) -> AsyncAzureOpenAI:
        """Get or create an asynchronous Azure client for the given model config"""
        cache_key = self._create_cache_key(model_config)
        
        if cache_key not in self._async_clients:
            self._async_clients[cache_key] = AsyncAzureOpenAI(
                api_key=model_config.get("api_key"),
                api_version=model_config.get("api_version"),
                azure_endpoint=model_config.get("azure_endpoint"),
                azure_deployment=model_config.get("azure_deployment"),
            )
        
        return self._async_clients[cache_key]
    
    def close_clients(self):
        """Close all cached clients to free resources"""
        # Close sync clients
        for client in self._clients.values():
            if hasattr(client, 'close'):
                client.close()
        self._clients.clear()
        
        # Close async clients
        for client in self._async_clients.values():
            if hasattr(client, 'close'):
                client.close()
        self._async_clients.clear()
    
    def _prepare_request_params(self, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Extract and prepare request parameters and system prompt"""
        request_kwargs = kwargs.copy()
        system_prompt = request_kwargs.pop("system", "")
        return request_kwargs, system_prompt
    
    def _get_model_capabilities(self, model_config: Dict[str, Any]) -> Tuple[bool, bool]:
        """Get model capabilities from config"""
        supports_reasoning = bool(model_config.get("reasoning_effort", False))
        supports_reasoning_summary = bool(model_config.get("reasoning_summary", False))
        return supports_reasoning, supports_reasoning_summary
    
    def _prepare_reasoning_params(self, kwargs: Dict[str, Any], request_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare reasoning parameters for API call"""
        reasoning_params = {}
        
        if "reasoning_effort" in kwargs:
            reasoning_params["effort"] = kwargs.get("reasoning_effort")
            request_kwargs.pop("reasoning_effort", None)
        
        if "summary_level" in kwargs:
            reasoning_params["summary"] = kwargs.get("summary_level")
            request_kwargs.pop("summary_level", None)
        
        return reasoning_params
    
    def _get_message_format(self, model_id: str, system_prompt: str, prompt: str) -> list:
        """Get the appropriate message format for the model"""
        if model_id == "o1-mini":
            # o1-mini requires combined system and user content
            return [{"role": "user", "content": f"{system_prompt}\n\n{prompt}"}]
        else:
            # Standard format with separate system and user messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            return messages
    
    def generate(self, prompt: str, model_id: str, **kwargs) -> Any:
        """Generate a response using the specified Azure model"""
        if not self.is_enabled():
            raise ValueError("Azure provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Azure model: {model_id}")
        
        model_config = self.models[model_id]
        request_kwargs, system_prompt = self._prepare_request_params(kwargs)
        supports_reasoning, supports_reasoning_summary = self._get_model_capabilities(model_config)
        client = self._get_client(model_config)

        if supports_reasoning_summary:
            reasoning_params = self._prepare_reasoning_params(kwargs, request_kwargs)
            response = client.responses.create(
                input=prompt,
                model=model_config.get("model_id"),
                reasoning=reasoning_params,
                **request_kwargs
            )
            return response

        elif supports_reasoning:
            # For o1 models that support reasoning but not summary
            messages = self._get_message_format(model_id, system_prompt, prompt)
            response = client.chat.completions.create(
                model=model_config.get("model_id"),
                messages=messages,
                **request_kwargs
            )
            return response

        else:
            # Regular models
            messages = self._get_message_format(model_id, system_prompt, prompt)
            response = client.chat.completions.create(
                model=model_config.get("model_id"),
                messages=messages,
                **request_kwargs
            )
            return response
    
    async def generate_async(self, prompt: str, model_id: str, **kwargs) -> Any:
        """Generate a response asynchronously using the specified Azure model"""
        if not self.is_enabled():
            raise ValueError("Azure provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Azure model: {model_id}")
        
        model_config = self.models[model_id]
        request_kwargs, system_prompt = self._prepare_request_params(kwargs)
        supports_reasoning, supports_reasoning_summary = self._get_model_capabilities(model_config)
        client = self._get_async_client(model_config)

        if supports_reasoning_summary:
            reasoning_params = self._prepare_reasoning_params(kwargs, request_kwargs)
            response = await client.responses.create(
                input=prompt,
                model=model_config.get("model_id"),
                reasoning=reasoning_params,
                **request_kwargs
            )
            return response

        elif supports_reasoning:
            # For o1 models that support reasoning but not summary
            messages = self._get_message_format(model_id, system_prompt, prompt)
            response = await client.chat.completions.create(
                model=model_config.get("model_id"),
                messages=messages,
                **request_kwargs
            )
            return response

        else:
            # Regular models
            messages = self._get_message_format(model_id, system_prompt, prompt)
            response = await client.chat.completions.create(
                model=model_config.get("model_id"),
                messages=messages,
                **request_kwargs
            )
            return response
