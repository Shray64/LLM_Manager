from llm_manager import LLMManager

# Initialize the manager
manager = LLMManager()

## AZURE ##

response = manager.generate("Explain quantum computing in simple terms", 
                            model="azure/o3",
                            temperature = 1,
                            max_completion_tokens = 300,
                            reasoning_effort = "low")

print(response)

# ANTHROPIC ##
# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="anthropic/claude-sonnet-4",
#                             max_tokens = 3000,
#                             thinking_tokens = 1024,
#                             )

# print(response)

## AWS BEDROCK ##

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="bedrock/claude-sonnet-3.7",
#                             max_tokens = 1000,
#                             # thinking_tokens = 32000,
#                             # temperature = 1)
# )
# print(response)

## ABACUS ##
# response = manager.generate("What are the benefits of containerization?",
#                             model="abacus/o3-higest",
#                             max_tokens = 3000,
#                             )
# print(response)


# manager.list_models()