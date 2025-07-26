import torch
from vllm import LLM, SamplingParams
from transformers import AutoTokenizer
from .base import BaseProvider

class VLLMProvider(BaseProvider):
    """Provider for vLLM models using direct vLLM library"""
    
    def __init__(self, config):
        super().__init__(config)
        self.models = config.get("models", {})
        self.llm_instances = {}
        self.tokenizers = {}
        
    def _get_llm_instance(self, model_id):
        """Get or create LLM instance for the model"""
        if model_id not in self.llm_instances:
            model_config = self.models[model_id]
            model_name = model_config.get("model_id")
            
            self.llm_instances[model_id] = LLM(
                model=model_name,
                max_model_len=model_config.get("max_model_len", 2048),
            )
            
        return self.llm_instances[model_id]
    
    def _get_tokenizer(self, model_id):
        """Get or create tokenizer for the model"""
        if model_id not in self.tokenizers:
            model_config = self.models[model_id]
            model_name = model_config.get("model_id")
            
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            tokenizer.pad_token = tokenizer.eos_token
            self.tokenizers[model_id] = tokenizer
            
        return self.tokenizers[model_id]
    
    def generate(self, prompt, model_id, **kwargs):
        """Generate a response using the specified vLLM model"""
        if not self.is_enabled():
            raise ValueError("vLLM provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown vLLM model: {model_id}")
        
        model_config = self.models[model_id]
        
        # Handle system prompt
        system_prompt = kwargs.pop("system", "")
        
        # Get LLM instance and tokenizer
        llm = self._get_llm_instance(model_id)
        tokenizer = self._get_tokenizer(model_id)
        
        # Create structured chat messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Apply chat template
        rendered_prompt = tokenizer.apply_chat_template(messages, tokenize=False)
        
        # Set up sampling parameters - merge config defaults with kwargs
        sampling_kwargs = {
            "max_tokens": kwargs.get("max_tokens", 512),
            "temperature": kwargs.get("temperature", 0.7),
        }
        sampling_kwargs.update(kwargs)  # Let kwargs override defaults
        
        sampling_params = SamplingParams(**sampling_kwargs)
        
        # Generate response
        outputs = llm.generate([rendered_prompt], sampling_params)
        
        return outputs[0].outputs[0].text.strip()
