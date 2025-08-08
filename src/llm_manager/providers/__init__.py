from .azure import AzureProvider
from .anthropic import AnthropicProvider
from .abacus import AbacusProvider
from .bedrock import BedrockProvider
# from .vLLM import VLLMProvider

PROVIDER_MAP = {
    "azure": AzureProvider,
    "anthropic": AnthropicProvider,
    "abacus": AbacusProvider,
    "bedrock": BedrockProvider,
    # "vLLM": VLLMProvider
}

__all__ = ["AzureProvider", 
           "AnthropicProvider", 
           "AbacusProvider", 
           "BedrockProvider", 
        #    "VLLMProvider",
           "PROVIDER_MAP"]

