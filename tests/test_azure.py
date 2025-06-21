from llm_manager import LLMManager

# Initialize the manager
manager = LLMManager()

##AZURE

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="azure/gpt4o",
#                             temperature = 0.3,
#                             max_completion_tokens = 3000,
#                             reasoning_effort = "medium")

# Generate a response using a model alias
response = manager.generate("Explain quantum computing in simple terms", 
                            model="anthropic/claude-sonnet-3.7",
                            max_tokens = 3000,)
                            # thinking_tokens = 1024)
print(response)

# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="bedrock/claude-sonnet-4",
#                             max_tokens = 10000)
# print(response)

# Try another model
# response = manager.generate("What are the benefits of containerization?",
#                             model="abacus/deepseek-r1",
#                             max_tokens = 32000,
#                             # thinking_tokens = 16000
#                             )
print(response)