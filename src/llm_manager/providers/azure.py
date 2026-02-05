from openai import AzureOpenAI, AsyncAzureOpenAI
from .base import BaseProvider
import warnings
import json
import httpx
from typing import Dict, Any, Optional, Tuple

class AzureProvider(BaseProvider):
    """Provider for Azure OpenAI and Azure Claude models"""

    # Claude models that support extended thinking
    CLAUDE_THINKING_MODELS = ["claude-opus-4.5", "claude-opus-4", "claude-sonnet-4.5", "claude-sonnet-4", "claude-sonnet-3.7"]

    def __init__(self, config):
        super().__init__(config)
        self.models = config.get("models", {})
        self._clients = {}  # Cache for sync clients
        self._async_clients = {}  # Cache for async clients
        self._http_clients = {}  # Cache for httpx clients (for Claude models)
        self._async_http_clients = {}  # Cache for async httpx clients (for Claude models)
    
    def _create_cache_key(self, model_config: Dict[str, Any]) -> Tuple:
        """Create a cache key based on the model configuration"""
        return (
            model_config.get("api_key"),
            model_config.get("api_version"),
            model_config.get("azure_endpoint"),
            model_config.get("azure_deployment")
        )

    def _is_claude_model(self, model_config: Dict[str, Any]) -> bool:
        """Check if the model is a Claude model based on config"""
        return model_config.get("model_type") == "claude"

    def _get_http_client(self, model_config: Dict[str, Any]) -> httpx.Client:
        """Get or create a synchronous httpx client for Claude models"""
        cache_key = self._create_cache_key(model_config)

        if cache_key not in self._http_clients:
            self._http_clients[cache_key] = httpx.Client(timeout=120.0)

        return self._http_clients[cache_key]

    def _get_async_http_client(self, model_config: Dict[str, Any]) -> httpx.AsyncClient:
        """Get or create an asynchronous httpx client for Claude models"""
        cache_key = self._create_cache_key(model_config)

        if cache_key not in self._async_http_clients:
            self._async_http_clients[cache_key] = httpx.AsyncClient(timeout=120.0)

        return self._async_http_clients[cache_key]
    
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

        # Close httpx clients (for Claude models)
        for client in self._http_clients.values():
            client.close()
        self._http_clients.clear()

        for client in self._async_http_clients.values():
            client.close()
        self._async_http_clients.clear()
    
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
    
    def _generate_claude(self, prompt: str, model_id: str, model_config: Dict[str, Any], **kwargs) -> Any:
        """Generate a response using Azure Claude API"""
        http_client = self._get_http_client(model_config)
        
        endpoint = model_config.get("azure_endpoint").rstrip("/")
        deployment = model_config.get("azure_deployment")
        api_version = model_config.get("api_version", "2024-12-01-preview")
        api_key = model_config.get("api_key")
        
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        
        # Build messages
        messages = []
        system_prompt = kwargs.pop("system", None)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build request body
        body = {
            "messages": messages,
            "max_tokens": kwargs.pop("max_tokens", 4096),
            "temperature": kwargs.pop("temperature", 0.7),
        }
        
        # Handle thinking/extended thinking for Claude models
        thinking_tokens = kwargs.pop("thinking_tokens", None)
        supports_thinking = model_config.get("thinking_supported", False) or model_id in self.CLAUDE_THINKING_MODELS
        
        if thinking_tokens and supports_thinking:
            body["temperature"] = 1.0  # Required for thinking mode
            body["thinking"] = {
                "type": "enabled", 
                "budget_tokens": thinking_tokens
            }
            print(f"Notice: Temperature set to 1.0 for thinking mode.")
        elif thinking_tokens and not supports_thinking:
            print(f"Warning: 'thinking_tokens' not supported by '{model_id}'. Parameter ignored.")
        
        # Add any additional kwargs
        body.update(kwargs)
        
        response = http_client.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        result = response.json()
        
        # Parse response - handle thinking if present
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            message = choice.get("message", {})
            
            # Check for thinking content
            if thinking_tokens and "thinking" in message:
                return {
                    "thinking": message.get("thinking", ""),
                    "response": message.get("content", "")
                }
            
            return message.get("content", "")
        
        return result

    async def _generate_claude_async(self, prompt: str, model_id: str, model_config: Dict[str, Any], **kwargs) -> Any:
        """Generate a response asynchronously using Azure Claude API"""
        http_client = self._get_async_http_client(model_config)
        
        endpoint = model_config.get("azure_endpoint").rstrip("/")
        deployment = model_config.get("azure_deployment")
        api_version = model_config.get("api_version", "2024-12-01-preview")
        api_key = model_config.get("api_key")
        
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }
        
        # Build messages
        messages = []
        system_prompt = kwargs.pop("system", None)
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Build request body
        body = {
            "messages": messages,
            "max_tokens": kwargs.pop("max_tokens", 4096),
            "temperature": kwargs.pop("temperature", 0.7),
        }
        
        # Handle thinking/extended thinking for Claude models
        thinking_tokens = kwargs.pop("thinking_tokens", None)
        supports_thinking = model_config.get("thinking_supported", False) or model_id in self.CLAUDE_THINKING_MODELS
        
        if thinking_tokens and supports_thinking:
            body["temperature"] = 1.0  # Required for thinking mode
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_tokens
            }
            print(f"Notice: Temperature set to 1.0 for thinking mode.")
        elif thinking_tokens and not supports_thinking:
            print(f"Warning: 'thinking_tokens' not supported by '{model_id}'. Parameter ignored.")
        
        # Add any additional kwargs
        body.update(kwargs)
        
        response = await http_client.post(url, headers=headers, json=body)
        response.raise_for_status()
        
        result = response.json()
        
        # Parse response - handle thinking if present
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            message = choice.get("message", {})
            
            # Check for thinking content
            if thinking_tokens and "thinking" in message:
                return {
                    "thinking": message.get("thinking", ""),
                    "response": message.get("content", "")
                }
            
            return message.get("content", "")
        
        return result

    def generate(self, prompt: str, model_id: str, **kwargs) -> Any:
        """Generate a response using the specified Azure model"""
        if not self.is_enabled():
            raise ValueError("Azure provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Azure model: {model_id}")
        
        model_config = self.models[model_id]
        
        # Route to Claude-specific handler if it's a Claude model
        if self._is_claude_model(model_config):
            return self._generate_claude(prompt, model_id, model_config, **kwargs)
        
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
        
        # Route to Claude-specific handler if it's a Claude model
        if self._is_claude_model(model_config):
            return await self._generate_claude_async(prompt, model_id, model_config, **kwargs)
        
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
