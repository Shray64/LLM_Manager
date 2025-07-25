# bedrock_provider.py
import boto3
import json
from botocore.exceptions import ClientError
from typing import Dict, Any, List, Optional, Union

class BedrockProvider:
    """Provider for AWS Bedrock models"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Bedrock provider with configuration"""
        self.config = config
        self.models = config.get("models", {})
        self._client = None
        # Models that support thinking parameter
        self.thinking_supported_models = ["claude-sonnet-4", "claude-opus-4", "claude-sonnet-3.7"]
    
    def is_enabled(self) -> bool:
        """Check if the provider is enabled"""
        return self.config.get("enabled", False)
    
    @property
    def client(self):
        """Get or create the Bedrock client"""
        if self._client is None:
            self._client = boto3.client(
                service_name="bedrock-runtime",
                region_name=self.config.get("region_name", "us-east-2"),
                aws_access_key_id=self.config.get("aws_access_key_id"),
                aws_secret_access_key=self.config.get("aws_secret_access_key")
            )
        return self._client
    
    def get_available_models(self) -> List[str]:
        """Get a list of available model IDs"""
        return list(self.models.keys())
    
    def generate(self, prompt: str, model_id: str, **kwargs) -> Union[str, Dict[str, str]]:
        """Generate a response using the specified Bedrock model"""
        if not self.is_enabled():
            raise ValueError("Bedrock provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Bedrock model: {model_id}")
    
        
        # Get model-specific config
        model_config = self.models[model_id]
        
        
        # Get the actual model ARN
        model_arn = model_config.get("model_id")
        
        # Check if this is a Claude model (based on ARN)
        is_claude = "anthropic" in model_arn.lower()
        
        # Initialize thinking flag
        using_thinking = False
        
        # Handle thinking parameter for Claude 4 models
        supports_thinking = any(model in model_id for model in self.thinking_supported_models)
        
        # Check if thinking_tokens is in kwargs
        if "thinking_tokens" in kwargs and supports_thinking and is_claude:
            
            thinking_tokens = kwargs.pop("thinking_tokens")
            # Track if thinking is being used
            using_thinking = True
            
            # Inform user about temperature change
            
        elif "thinking_tokens" in kwargs and not supports_thinking and is_claude:
            # Remove the parameter and warn the user
            kwargs.pop("thinking_tokens")
            compatible_models = ", ".join(self.thinking_supported_models)
            warning_msg = (
                f"Warning: 'thinking_tokens' parameter is not supported by the model '{model_id}'. "
                f"This parameter is only compatible with the following models: {compatible_models}. "
                f"The parameter has been ignored for this request."
            )
            print(warning_msg)
        
        # Prepare the payload based on model type
        if is_claude:
            payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "system": kwargs.get("system_message", ""),
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
        
                
            # Add thinking configuration if applicable
            if using_thinking:
                payload["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_tokens
                }
                
            # Add optional parameters if provided
            for param in ["top_k", "stop_sequences"]:
                if param in kwargs:
                    payload[param] = kwargs[param]
        else:
            # Generic payload for other models
            # This would need to be customized based on the specific model requirements
            payload = {
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "system": kwargs.get("system_message", ""),
            }
            
            # Add other model-specific parameters as needed
            for param in ["top_k", "stop", "frequency_penalty", "presence_penalty"]:
                if param in kwargs:
                    payload[param] = kwargs[param]
        
        try:
            response = self.client.invoke_model(
                modelId=model_arn,
                body=json.dumps(payload),
                contentType="application/json",
                accept="application/json",
            )
            
            # Parse the response body
            response_body = json.loads(response['body'].read())
            
            # Extract the response text based on model type
            if is_claude:
                if using_thinking:
                    # Handle response with thinking
                    if 'content' in response_body:
                        thinking_text = None
                        response_text = None
                        
                        for content_block in response_body['content']:
                            if content_block.get('type') == 'thinking':
                                thinking_text = content_block.get('thinking', '')
                            elif content_block.get('type') == 'text':
                                response_text = content_block.get('text', '')
                        
                        return {
                            "thinking": thinking_text,
                            "response": response_text
                        }
                else:
                    # Standard response handling
                    if 'content' in response_body:
                        # Extract text from content array (Claude 3/4 format)
                        result = ""
                        for content_block in response_body['content']:
                            if content_block.get('type') == 'text':
                                result += content_block.get('text', '')
                        return result
                    elif 'completion' in response_body:
                        # Claude 2 format
                        return response_body['completion']
            
            # Generic fallback for other models
            # This would need to be customized based on the specific model response format
            return json.dumps(response_body)
            
        except ClientError as e:
            error_message = f"Bedrock error: {e.response['Error']['Message']}"
            raise Exception(error_message)
