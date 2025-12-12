# bedrock_provider.py
import boto3
import json
from botocore.exceptions import ClientError
from .base import BaseProvider
from typing import Dict, Any, List, Optional, Tuple
import aioboto3

class BedrockProvider(BaseProvider):
    """Provider for AWS Bedrock models"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Bedrock provider with configuration"""
        super().__init__(config)
        self.models = config.get("models", {})
        self._clients = {}  # Cache for sync clients
        self._async_clients = {}  # Cache for async clients
        # Default models that support thinking parameter (used as fallback if config flag not provided)
        # self._default_thinking_supported_models = ["claude-sonnet-4", "claude-opus-4", "claude-sonnet-3.7"]
    
    def _create_cache_key(self, model_config: Dict[str, Any]) -> Tuple:
        """Create a cache key based on the model configuration"""
        return (
            model_config.get("region_name", self.config.get("region_name", "us-east-2")),
            model_config.get("aws_access_key_id", self.config.get("aws_access_key_id")),
            model_config.get("aws_secret_access_key", self.config.get("aws_secret_access_key"))
        )
    
    def _get_client(self, model_config: Dict[str, Any]):
        """Get or create a synchronous Bedrock client for the given model config"""
        cache_key = self._create_cache_key(model_config)
        
        if cache_key not in self._clients:
            self._clients[cache_key] = boto3.client(
                service_name="bedrock-runtime",
                region_name=model_config.get("region_name", self.config.get("region_name", "us-east-2")),
                aws_access_key_id=model_config.get("aws_access_key_id", self.config.get("aws_access_key_id")),
                aws_secret_access_key=model_config.get("aws_secret_access_key", self.config.get("aws_secret_access_key"))
            )
        
        return self._clients[cache_key]
    
    def _get_async_client(self, model_config: Dict[str, Any]):
        """Create a fresh asynchronous Bedrock client for the given model config"""
        # Create a fresh client for each request to avoid coroutine reuse issues
        session = aioboto3.Session()
        return session.client(
            service_name="bedrock-runtime",
            region_name=model_config.get("region_name", self.config.get("region_name", "us-east-2")),
            aws_access_key_id=model_config.get("aws_access_key_id", self.config.get("aws_access_key_id")),
            aws_secret_access_key=model_config.get("aws_secret_access_key", self.config.get("aws_secret_access_key"))
        )
    
    def close_clients(self):
        """Close all cached clients to free resources"""
        # Close sync clients
        for client in self._clients.values():
            if hasattr(client, 'close'):
                client.close()
        self._clients.clear()
        
        # Note: Async clients are now created fresh for each request, so no need to close cached ones
    
    def get_available_models(self) -> List[str]:
        """Get a list of available model IDs"""
        return list(self.models.keys())
    
    def _prepare_request_params(self, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Extract and prepare request parameters and system prompt"""
        request_kwargs = kwargs.copy()
        system_prompt = request_kwargs.pop("system", request_kwargs.pop("system_message", ""))
        return request_kwargs, system_prompt
    
    def _get_model_capabilities(self, model_id: str, model_arn: str, model_config: Dict[str, Any]) -> Tuple[bool, bool]:
        """Get model capabilities.

        supports_thinking is read from config if present via 'thinking_supported'.
        Falls back to a conservative default list for backward compatibility.
        """
        is_claude = "anthropic" in model_arn.lower()
        if "thinking_supported" in model_config:
            supports_thinking = bool(model_config.get("thinking_supported")) and is_claude
        else:
            # Fallback to previous heuristic list when the config flag is absent
            supports_thinking = any(model in model_id for model in self._default_thinking_supported_models) and is_claude
        return is_claude, supports_thinking
    
    def _prepare_thinking_params(self, kwargs: Dict[str, Any], request_kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Prepare thinking parameters for API call"""
        thinking_params = {}
        using_thinking = False
        
        if "thinking_tokens" in kwargs:
            thinking_tokens = kwargs.get("thinking_tokens")
            request_kwargs.pop("thinking_tokens", None)
            thinking_params = {
                "type": "enabled",
                "budget_tokens": thinking_tokens
            }
            using_thinking = True
        
        return thinking_params, using_thinking
    
    def _prepare_payload(self, prompt: str, model_arn: str, is_claude: bool, system_prompt: str, 
                        thinking_params: Dict[str, Any], using_thinking: bool, **kwargs) -> Dict[str, Any]:
        """Prepare the payload for the API call"""
        if is_claude:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Add thinking configuration if applicable
            if using_thinking:
                payload["thinking"] = thinking_params
                
            # Add optional parameters if provided
            for param in ["top_k", "stop_sequences"]:
                if param in kwargs:
                    payload[param] = kwargs[param]
        else:
            # Generic payload for other models
            payload = {
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "system": system_prompt,
            }
            
            # Add other model-specific parameters as needed
            for param in ["top_k", "stop", "frequency_penalty", "presence_penalty"]:
                if param in kwargs:
                    payload[param] = kwargs[param]
        
        return payload
    
    def generate(self, prompt: str, model_id: str, **kwargs) -> Any:
        """Generate a response using the specified Bedrock model"""
        if not self.is_enabled():
            raise ValueError("Bedrock provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Bedrock model: {model_id}")
        
        # Get model-specific config
        model_config = self.models[model_id]
        model_arn = model_config.get("model_id")
        
        # If caller provided a raw payload, send it as-is (dict or JSON string)
        if "payload" in kwargs:
            user_payload = kwargs.get("payload")
            client = self._get_client(model_config)
            try:
                if isinstance(user_payload, str):
                    body = user_payload
                else:
                    body = json.dumps(user_payload)
                response = client.invoke_model(
                    modelId=model_arn,
                    body=body,
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = json.loads(response['body'].read())
                return response_body
            except ClientError as e:
                error_message = f"Bedrock error: {e.response['Error']['Message']}"
                raise Exception(error_message)

        # Prepare request parameters
        request_kwargs, system_prompt = self._prepare_request_params(kwargs)
        is_claude, supports_thinking = self._get_model_capabilities(model_id, model_arn, model_config)
        
        # Handle thinking parameters
        if "thinking_tokens" in kwargs and not supports_thinking and is_claude:
            # Remove the parameter and warn the user
            kwargs.pop("thinking_tokens")
            # Prefer models explicitly flagged in config; else fallback to default list
            explicitly_flagged = [m for m, cfg in self.models.items() if cfg.get("thinking_supported")]
            compatible_models = ", ".join(explicitly_flagged or self._default_thinking_supported_models)
            warning_msg = (
                f"Warning: 'thinking_tokens' parameter is not supported by the model '{model_id}'. "
                f"This parameter is only compatible with the following models: {compatible_models}. "
                f"The parameter has been ignored for this request."
            )
            print(warning_msg)
        
        thinking_params, using_thinking = self._prepare_thinking_params(kwargs, request_kwargs)
        
        # Prepare payload
        payload = self._prepare_payload(
            prompt, model_arn, is_claude, system_prompt, 
            thinking_params, using_thinking, **request_kwargs
        )
        
        # Get client and make request
        client = self._get_client(model_config)
        
        try:
            response = client.invoke_model(
                modelId=model_arn,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )
            
            # Parse the response body
            response_body = json.loads(response['body'].read())
            
            # Return the raw response body instead of processed text
            return response_body
            
        except ClientError as e:
            error_message = f"Bedrock error: {e.response['Error']['Message']}"
            raise Exception(error_message)
    
    async def generate_async(self, prompt: str, model_id: str, **kwargs) -> Any:
        """Generate a response asynchronously using the specified Bedrock model"""
        if not self.is_enabled():
            raise ValueError("Bedrock provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Bedrock model: {model_id}")
        
        # Get model-specific config
        model_config = self.models[model_id]
        model_arn = model_config.get("model_id")
        
        # If caller provided a raw payload, send it as-is (dict or JSON string)
        if "payload" in kwargs:
            async_client = self._get_async_client(model_config)
            try:
                async with async_client as client:
                    if isinstance(user_payload, str):
                        body = user_payload
                    else:
                        body = json.dumps(user_payload)
                    response = await client.invoke_model(
                        modelId=model_arn,
                        body=body,
                        contentType="application/json",
                        accept="application/json",
                    )
                    response_body = json.loads(await response['body'].read())
                    return response_body
            except ClientError as e:
                error_message = f"Bedrock error: {e.response['Error']['Message']}"
                raise Exception(error_message)

        # Prepare request parameters
        request_kwargs, system_prompt = self._prepare_request_params(kwargs)
        is_claude, supports_thinking = self._get_model_capabilities(model_id, model_arn, model_config)
        
        # Handle thinking parameters
        if "thinking_tokens" in kwargs and not supports_thinking and is_claude:
            # Remove the parameter and warn the user
            kwargs.pop("thinking_tokens")
            # Prefer models explicitly flagged in config; else fallback to default list
            explicitly_flagged = [m for m, cfg in self.models.items() if cfg.get("thinking_supported")]
            compatible_models = ", ".join(explicitly_flagged or self._default_thinking_supported_models)
            warning_msg = (
                f"Warning: 'thinking_tokens' parameter is not supported by the model '{model_id}'. "
                f"This parameter is only compatible with the following models: {compatible_models}. "
                f"The parameter has been ignored for this request."
            )
            print(warning_msg)
        
        thinking_params, using_thinking = self._prepare_thinking_params(kwargs, request_kwargs)
        
        # Prepare payload
        payload = self._prepare_payload(
            prompt, model_arn, is_claude, system_prompt, 
            thinking_params, using_thinking, **request_kwargs
        )
        
        # Get async client and make request
        async_client = self._get_async_client(model_config)
        
        try:
            async with async_client as client:
                response = await client.invoke_model(
                    modelId=model_arn,
                    body=json.dumps(payload),
                    contentType="application/json",
                    accept="application/json",
                )
                
                # Parse the response body
                response_body = json.loads(await response['body'].read())
                
                # Return the raw response body instead of processed text
                return response_body
                
        except ClientError as e:
            error_message = f"Bedrock error: {e.response['Error']['Message']}"
            raise Exception(error_message)
