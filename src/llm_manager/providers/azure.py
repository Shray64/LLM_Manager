from openai import AzureOpenAI
from .base import BaseProvider

class AzureProvider(BaseProvider):
    """Provider for Azure OpenAI models"""
    
    def __init__(self, config):
        super().__init__(config)
        self.models = config.get("models", {})
    
    def generate(self, prompt, model_id, **kwargs):
        """Generate a response using the specified Azure model"""
        if not self.is_enabled():
            raise ValueError("Azure provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Azure model: {model_id}")
        
        model_config = self.models[model_id]
        
        client = AzureOpenAI(
            api_key=model_config.get("api_key"),
            api_version=model_config.get("api_version"),
            azure_endpoint=model_config.get("azure_endpoint"),
            azure_deployment=model_config.get("azure_deployment"),
        )
        
        response = client.chat.completions.create(
            model=model_config.get("model_id"),
            messages=[{"role": "user", "content": prompt}],
            **kwargs
        )
        
        return response.choices[0].message.content
