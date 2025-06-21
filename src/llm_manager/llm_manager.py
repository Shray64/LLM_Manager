from .utils.config import load_config
from .providers import PROVIDER_MAP
from retry import retry

class LLMManager:
    "Manager for interacting with various LLM providers"

    def __init__(self, config_path=None):
        """Initialize the LLM Manager with the given configuration"""
        self.config = load_config(config_path)
        self.providers = {}
        self._initialize_providers()


    def _initialize_providers(self):
        """Initialize all enabled providers"""
        for provider_name, provider_config in self.config.get("providers", {}).items():
            if provider_name in PROVIDER_MAP and provider_config.get("enabled", False):
                provider_class = PROVIDER_MAP[provider_name]
                self.providers[provider_name] = provider_class(provider_config)


    def generate(self, prompt, model=None, **kwargs):
        """Generate a response using the specified model"""
        if model is None:
            model = self.config.get("default_model")
        
        # Resolve model alias if needed
        if model in self.config.get("model_aliases", {}):
            model_path = self.config["model_aliases"][model]
            provider_name, model_id = model_path.split("/")
        else:
            # Assume format is provider/model_id
            try:
                provider_name, model_id = model.split("/")
            except ValueError:
                raise ValueError(f"Invalid model format: {model}. Use 'provider/model_id' format or a defined alias.")
        
        # Check if provider exists and is enabled
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found or not enabled")
        
        # Generate the response
        return self.providers[provider_name].generate(prompt, model_id, **kwargs)
    

    def list_models(self):
        """List all available models"""
        models = {}
        for provider_name, provider in self.providers.items():
            if hasattr(provider, 'models'):
                models[provider_name] = list(provider.models.keys())
        return models
    
    def list_aliases(self):
        """List all model aliases"""
        return self.config.get("model_aliases", {})