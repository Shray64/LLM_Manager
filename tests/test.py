from llm_manager import LLMManager
import asyncio

# Initialize the manager
manager = LLMManager()

# AZURE ##

# response = manager.generate("Prove the pythagoras theorem", 
#                             model="ollama/codellama",
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

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="bedrock/claude-sonnet-3.7",
#                             # max_comp_tokens = 1000,
#                             max_tokens = 10000, 
#                             thinking_tokens = 3200,
#                             temperature = 1)
# # )
# print(response)

## ABACUS ##
response = manager.generate("What are the benefits of containerization?",
                            model="abacus/gemini-3-flash",
                            max_tokens = 3000,
                            )
print(response)


# manager.list_models()

# vLLM ##

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="vLLM/qwen2-7b")


# print(response)
