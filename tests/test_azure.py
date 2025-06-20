from llm_manager import LLMManager

# Initialize the manager
manager = LLMManager()

# Generate a response using a model alias
# response = manager.generate("Explain quantum computing in simple terms", 
#                             model="anthropic/claude_3_7",
#                             max_tokens = 20000, 
#                             thinking_tokens = 800)
# print(response)

# Try another model
response = manager.generate("What are the benefits of containerization?",
                            model="azure/gpt4o",
                            reasoning_effort = "high")
print(response)