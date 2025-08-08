from llm_manager import LLMManager

# Initialize the manager
manager = LLMManager()

# AZURE ##

# response = manager.generate("Prove the pythagoras theorem", 
#                             model="azure/o3",
#                             temperature = 1,
#                             max_completion_tokens = 3000,
#                             reasoning_effort = "medium")

# print(response.get('reasoning_tokens', 0))

# ANTHROPIC ##
# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="anthropic/claude-sonnet-4",
#                             max_tokens = 3000,
#                             thinking_tokens = 1024,
#                             )

# print(response)

## AWS BEDROCK ##

response = manager.generate("Explain quantum computing in simple terms", 
                            model="bedrock/claude-sonnet-3.7",
                            # max_tokens = 1000,
                            # thinking_tokens = 32000,
                            # temperature = 1)
)
print(response)

## ABACUS ##
# response = manager.generate("What are the benefits of containerization?",
#                             model="abacus/o3-higest",
#                             max_tokens = 3000,
#                             )
# print(response)


# manager.list_models()

# vLLM ##

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="vLLM/qwen2-7b")


# print(response)
