import abacusai
from .base import BaseProvider

class AbacusProvider(BaseProvider):

    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.models = config.get("models", {})

    def generate(self, prompt, model_id, **kwargs):
        if not self.is_enabled():
            raise ValueError("Abacus provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Abacus model: {model_id}")
        
        model_config = self.models[model_id]
        client = abacusai.ApiClient(api_key=self.api_key)

        print(model_config.get("model_id"))

        response = client.evaluate_prompt(
            prompt=prompt,
            llm_name="GEMINI_3_FLASH",
            **kwargs
        )

        return response.content

