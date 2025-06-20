from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """Base class for all LLM providers"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.get("enabled", False)
    
    @abstractmethod
    def generate(self, prompt, model_id, **kwargs):
        """Generate a response using the specified model"""
        pass
    
    def is_enabled(self):
        """Check if this provider is enabled"""
        return self.enabled
