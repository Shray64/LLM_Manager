from anthropic import Anthropic
from .base import BaseProvider

class AnthropicProvider(BaseProvider):

    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.models = config.get("models", {})

    def generate(self, prompt, model_id, **kwargs):
        '''Generate a response using the specified Anthropic model'''

        if not self.is_enabled():
            raise ValueError("Anthropic provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Anthropic model: {model_id}")
        
        model_config = self.models[model_id]
        client = Anthropic(api_key=self.api_key)

        message_kwargs = {
            "model": model_config.get("model_id"),
            "max_tokens": model_config.get("max_tokens", 10000),
            "temperature": model_config.get("temperature", 0.7),
            "system": model_config.get("system", ""),
            "messages": [{"role": "user", "content": prompt}],
        }

        # Add thinking if specified
        if "thinking" in model_config:
            message_kwargs["thinking"] = model_config["thinking"]
        
        # Override with any passed kwargs
        message_kwargs.update(kwargs)
        
        message = client.messages.create(**message_kwargs)

        # Handle different return types based on thinking
        if "thinking" in model_config:
            return message
        else:
            return message.content[0].text




