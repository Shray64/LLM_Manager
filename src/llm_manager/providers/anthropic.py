from anthropic import Anthropic
from .base import BaseProvider

class AnthropicProvider(BaseProvider):
    """Provider for Anthropic Claude models"""
    
    def __init__(self, config):
        super().__init__(config)
        self.models = config.get("models", {})
        # Models that support thinking parameter
        self.thinking_supported_models = ["claude-sonnet-3.7"]
    
    def generate(self, prompt, model_id, **kwargs):
        """Generate a response using the specified Anthropic model"""
        if not self.is_enabled():
            raise ValueError("Anthropic provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Anthropic model: {model_id}")
        
        model_config = self.models[model_id]
        api_key = model_config.get("api_key")

        merged_config = {**model_config, **kwargs}
        
        client = Anthropic(api_key=api_key)

        # print(merged_config.get("system", ""))
        
        # Prepare request parameters
        request_params = {
            "model": merged_config.get("model_id"),
            "max_tokens": merged_config.get("max_tokens", 1000),
            "temperature": merged_config.get("temperature", 0.7),   
            "messages": [{"role": "user", "content": prompt}],
            "stream": merged_config.get("stream", False)
        }
        
        # Add system prompt if provided
        if merged_config.get("system"):
            request_params["system"] = merged_config.get("system")
        
        # Handle thinking parameter
        supports_thinking = any(model in model_id for model in self.thinking_supported_models)
        model_name = merged_config.get("model_id", "").lower()

        using_thinking = False
        
        # Check if thinking_tokens is in kwargs
        if "thinking_tokens" in kwargs and supports_thinking:
            original_temp = request_params.get("temperature", 0.7)
            request_params['temperature'] = 1.0

            request_params["thinking"] = {
                "type": "enabled",
                "budget_tokens": kwargs.pop("thinking_tokens")
            }
            # Track if thinking is being used
            using_thinking = True

            request_params["stream"] = True

            # Inform user about temperature change
            print(f'''Notice: Temperature has been set to 1.0 (from {original_temp}) because thinking mode requires it.
                   Also using streaming mode by default when in thinking mode.''')

        elif "thinking_tokens" in kwargs and not supports_thinking:
            # Remove the parameter and warn the user
            kwargs.pop("thinking_tokens")
            compatible_models = ", ".join(self.thinking_supported_models)
            warning_msg = (
                f"Warning: 'thinking_tokens' parameter is not supported by the model '{model_name}'. "
                f"This parameter is only compatible with the following models: {compatible_models}. "
                f"The parameter has been ignored for this request."
            )
            print(warning_msg)
        
        # Add any remaining kwargs to the request
        request_params.update(kwargs)
        
        # Make the API call
        try:  
              
            # Handle response differently if thinking was used
            if using_thinking:
                stream = client.messages.create(**request_params)
                # Return both thinking and response

                thinking_text = ""
                response_text = ""
                for chunk in stream:
                    if chunk.type == "content_block_delta" and hasattr(chunk.delta, "thinking"):
                        thinking_text += chunk.delta.thinking
                    if chunk.type == "content_block_delta" and hasattr(chunk.delta, "text"):
                        response_text += chunk.delta.text
                    
                return {
                    "thinking": thinking_text,
                    "response": response_text
                }
            else:
                # Return just the response text
                message = client.messages.create(**request_params)
                return message.content[0].text
                
        except Exception as e:
            raise Exception(f"Error calling Anthropic API: {str(e)}")
