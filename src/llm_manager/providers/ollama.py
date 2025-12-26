import requests
from .base import BaseProvider
from typing import Dict, Any, Optional, Tuple

class OllamaProvider(BaseProvider):
    """Provider for Ollama local models"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Ollama provider with configuration"""
        super().__init__(config)
        self.models = config.get("models", {})
        self.base_url = config.get("base_url", "http://localhost:11434")
        self._clients = {}  # Cache for sync clients (requests sessions)
    
    def _create_cache_key(self, model_config: Dict[str, Any]) -> Tuple:
        """Create a cache key based on the model configuration"""
        return (
            model_config.get("base_url", self.base_url),
        )
    
    def _get_client(self, model_config: Dict[str, Any]):
        """Get or create a requests session for the given model config"""
        cache_key = self._create_cache_key(model_config)
        
        if cache_key not in self._clients:
            session = requests.Session()
            # Set timeout for requests
            session.timeout = model_config.get("timeout", 300)
            self._clients[cache_key] = session
        
        return self._clients[cache_key]
    
    def close_clients(self):
        """Close all cached clients to free resources"""
        for session in self._clients.values():
            if hasattr(session, 'close'):
                session.close()
        self._clients.clear()
    
    def get_available_models(self) -> list:
        """Get a list of available model IDs"""
        return list(self.models.keys())
    
    def _prepare_request_params(self, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Extract and prepare request parameters and system prompt"""
        request_kwargs = kwargs.copy()
        system_prompt = request_kwargs.pop("system", request_kwargs.pop("system_message", ""))
        return request_kwargs, system_prompt
    
    def _prepare_payload(self, prompt: str, model_id: str, system_prompt: str, **kwargs) -> Dict[str, Any]:
        """Prepare the payload for the Ollama API call"""
        payload = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,  # Non-streaming for sync calls
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        # Prepare options dict for Ollama
        options = {}
        
        # Map common parameters to Ollama options
        if "temperature" in kwargs:
            options["temperature"] = kwargs.pop("temperature")
        if "max_tokens" in kwargs:
            options["num_predict"] = kwargs.pop("max_tokens")
        elif "num_predict" in kwargs:
            options["num_predict"] = kwargs.pop("num_predict")
        if "top_p" in kwargs:
            options["top_p"] = kwargs.pop("top_p")
        if "top_k" in kwargs:
            options["top_k"] = kwargs.pop("top_k")
        if "repeat_penalty" in kwargs:
            options["repeat_penalty"] = kwargs.pop("repeat_penalty")
        
        # Add any remaining kwargs to options
        if kwargs:
            options.update(kwargs)
        
        # Only add options if there are any
        if options:
            payload["options"] = options
        
        return payload
    
    def generate(self, prompt: str, model_id: str, **kwargs) -> Any:
        """Generate a response using the specified Ollama model"""
        if not self.is_enabled():
            raise ValueError("Ollama provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Ollama model: {model_id}")
        
        # Get model-specific config
        model_config = self.models[model_id]
        actual_model_id = model_config.get("model_id", model_id)
        base_url = model_config.get("base_url", self.base_url)
        
        # Prepare request parameters
        request_kwargs, system_prompt = self._prepare_request_params(kwargs)
        
        # Prepare payload
        payload = self._prepare_payload(
            prompt, actual_model_id, system_prompt, **request_kwargs
        )
        
        # Get client and make request
        session = self._get_client(model_config)
        api_url = f"{base_url}/api/generate"
        
        try:
            response = session.post(api_url, json=payload)
            response.raise_for_status()  # Raise exception for bad status codes
            
            response_data = response.json()

            return response_data
            
        except requests.exceptions.RequestException as e:
            error_message = f"Ollama error: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_message = f"Ollama error: {error_detail.get('error', str(e))}"
                except:
                    error_message = f"Ollama error: {e.response.text if hasattr(e.response, 'text') else str(e)}"
            raise Exception(error_message)

