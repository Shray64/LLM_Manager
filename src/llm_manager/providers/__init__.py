from .azure import AzureProvider
from .anthropic import AnthropicProvider
from .abacus import AbacusProvider
from .bedrock import BedrockProvider
from .ollama import OllamaProvider
# from .vLLM import VLLMProvider

PROVIDER_MAP = {
    "azure": AzureProvider,
    "anthropic": AnthropicProvider,
    "abacus": AbacusProvider,
    "bedrock": BedrockProvider,
    "ollama": OllamaProvider,
    # "vLLM": VLLMProvider
}

__all__ = ["AzureProvider", 
           "AnthropicProvider", 
           "AbacusProvider", 
           "BedrockProvider",
           "OllamaProvider",
        #    "VLLMProvider",
           "PROVIDER_MAP"]

