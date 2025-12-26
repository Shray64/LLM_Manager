# LLM Manager

A unified Python library for interacting with multiple Large Language Model (LLM) providers through a single, consistent interface.

## Features

- **Multi-Provider Support**: Works with Azure OpenAI, Anthropic, AWS Bedrock, HuggingFace, Ollama, vLLM, and Abacus
- **Unified API**: Single interface for all providers
- **Async Support**: Both synchronous and asynchronous operations
- **Client Caching**: Automatic client connection caching for improved performance
- **Model Aliases**: Define custom aliases for your models
- **Configuration-Based**: Easy setup via YAML configuration file

## Installation

```bash
pip install llm-manager
```

Or install from source:

```bash
git clone <repository-url>
cd LLM_Manager
pip install -e .
```

## Quick Start

```python
from llm_manager import LLMManager

# Initialize the manager
manager = LLMManager()

# Generate a response
response = manager.generate(
    prompt="What is artificial intelligence?",
    model="azure/gpt4o"
)

print(response)
```

## Async Usage

```python
import asyncio
from llm_manager import LLMManager

async def main():
    manager = LLMManager()
    
    # Generate responses asynchronously
    response = await manager.generate_async(
        prompt="Explain machine learning in one sentence",
        model="azure/gpt4o"
    )
    
    print(response)

asyncio.run(main())
```

## Configuration

The package uses a `config.yaml` file to configure providers and models. Set up your API keys and endpoints in the configuration file or via environment variables.

Example configuration structure:
```yaml
providers:
  azure:
    enabled: true
    models:
      gpt4o:
        api_key: "${AZURE_API_KEY}"
        azure_endpoint: "${AZURE_API_BASE}"
        # ... other settings
```

## Supported Providers

- **Azure OpenAI**: GPT-4, GPT-3.5, O1, O3, and more
- **Anthropic**: Claude models
- **AWS Bedrock**: Claude Sonnet, Claude Haiku, and other Bedrock models
- **HuggingFace**: Models from HuggingFace Hub
- **Ollama**: Local models via Ollama
- **vLLM**: High-performance inference server
- **Abacus**: Abacus AI models

## Examples

See the `examples/` directory for more usage examples:
- `client_caching_example.py`: Demonstrates client caching benefits
- `sciab_chatbot.py`: Example chatbot using multiple models

## Requirements

- Python 3.8+
- See `setup.py` for full dependency list

## License

MIT
