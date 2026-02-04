from llm_manager import LLMManager
import asyncio

# Initialize the manager
manager = LLMManager()

# Ollama ##

# response = manager.generate("Prove the pythagoras theorem", 
#                             model="ollama/qwen2.5",
#                             )
# print(response)

# AZURE ##

# response = manager.generate("Prove the pythagoras theorem", 
#                             model="azure/o1",
#                             # max_output_tokens = 3000,
#                             # reasoning_effort = "high",
#                             # summary_level = "detailed",
#                             # max_completion_tokens = 3000
#                             )
# print(response)

# ANTHROPIC ##
# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="anthropic/claude-sonnet-4",
#                             # max_tokens = 3000,
#                             # thinking_tokens = 1024,
#                             )

# print(response)

# AWS BEDROCK ##

response = manager.generate("Explain quantum computing in simple terms", 
                            model="bedrock/claude-opus-4.5",
                            # max_comp_tokens = 1000,
                            max_tokens = 10000, 
                            thinking_tokens = 3200,
                            temperature = 1)
# )
print(response)

## ABACUS ##
# response = manager.generate("What are the benefits of containerization?",
#                             model="abacus/deepseek-r1",
#                             )
# print(response)


# manager.list_models()

# vLLM ##

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="vLLM/qwen2-7b")


# print(response)
