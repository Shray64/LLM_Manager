#!/usr/bin/env python3
"""
Simple example of Azure async functionality
"""

import asyncio
import time
from llm_manager import LLMManager

async def single_async_call():
    """Example of a single async call"""
    print("=== Single Async Call ===")
    
    manager = LLMManager()
    
    start_time = time.time()
    response = await manager.generate_async(
        "Explain quantum computing in simple terms", 
        model="azure/gpt4o",
        max_tokens=500,
        temperature=0.7
    )
    end_time = time.time()
    
    # Extract content from raw API response
    if hasattr(response, 'choices') and response.choices:
        content = response.choices[0].message.content
        print(f"Response: {content}")
    else:
        print(f"Response: {response}")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print()

async def multiple_concurrent_calls():
    """Example of multiple concurrent async calls"""
    print("=== Multiple Concurrent Calls ===")
    
    manager = LLMManager()
    
    prompts = [
        "What is machine learning?",
        "What is artificial intelligence?",
        "What is deep learning?",
        "What is natural language processing?"
    ]
    
    start_time = time.time()
    
    # Create async tasks
    tasks = [
        manager.generate_async(prompt, model="azure/gpt4o", max_tokens=300)
        for prompt in prompts
    ]
    
    # Execute concurrently
    responses = await asyncio.gather(*tasks)
    
    end_time = time.time()
    
    print(f"Processed {len(prompts)} requests in {end_time - start_time:.2f} seconds")
    for i, response in enumerate(responses):
        # Extract content from raw API response
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            print(f"Response {i+1}: {content[:100]}...")
        else:
            print(f"Response {i+1}: {str(response)[:100]}...")
    print()

async def reasoning_model_async():
    """Example of async call with reasoning model"""
    print("=== Reasoning Model Async Call ===")
    
    manager = LLMManager()
    
    start_time = time.time()
    response = await manager.generate_async(
        "Prove the Pythagorean theorem step by step",
        model="azure/gpt-5",
        max_output_tokens=2000,
        reasoning_effort="medium"
    )
    end_time = time.time()
    
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    
    # Handle different response types from raw API responses
    if hasattr(response, 'output') and response.output:
        # This is a responses.create() response (reasoning with summary)
        if len(response.output) >= 2:
            thinking = response.output[0].summary[0].text if response.output[0].summary else ""
            content = response.output[1].content[0].text
            print(f"Thinking: {thinking[:200]}...")
            print(f"Response: {content[:200]}...")
        else:
            print(f"Response: {str(response)[:200]}...")
    elif hasattr(response, 'choices') and response.choices:
        # This is a chat.completions.create() response
        content = response.choices[0].message.content
        print(f"Response: {content[:200]}...")
    else:
        print(f"Response: {str(response)[:200]}...")
    print()

async def performance_comparison():
    """Compare synchronous vs asynchronous performance"""
    print("=== Performance Comparison ===")
    
    manager = LLMManager()
    prompts = [
        "What is Python?",
        "What is JavaScript?",
        "What is Rust?",
        "What is Go?"
    ]
    
    # Synchronous approach
    print("Synchronous approach:")
    start_time = time.time()
    sync_responses = []
    for prompt in prompts:
        response = manager.generate(prompt, model="azure/gpt4o", max_tokens=200)
        # Extract content from raw API response
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            sync_responses.append(content)
        else:
            sync_responses.append(str(response))
    sync_time = time.time() - start_time
    print(f"Time taken: {sync_time:.2f} seconds")
    
    # Asynchronous approach
    print("\nAsynchronous approach:")
    start_time = time.time()
    async_tasks = [
        manager.generate_async(prompt, model="azure/gpt4o", max_tokens=200)
        for prompt in prompts
    ]
    async_responses = await asyncio.gather(*async_tasks)
    async_time = time.time() - start_time
    print(f"Time taken: {async_time:.2f} seconds")
    
    # Extract content from async responses for comparison
    async_contents = []
    for response in async_responses:
        if hasattr(response, 'choices') and response.choices:
            content = response.choices[0].message.content
            async_contents.append(content)
        else:
            async_contents.append(str(response))
    
    print(f"\nPerformance improvement: {sync_time/async_time:.2f}x faster")
    print()

async def main():
    """Run all examples"""
    print("Azure Async Examples")
    print("=" * 30)
    
    try:
        await single_async_call()
        await multiple_concurrent_calls()
        await reasoning_model_async()
        await performance_comparison()
        
    except Exception as e:
        print(f"Error running examples: {e}")
        print("This could be due to:")
        print("- Missing or invalid Azure API keys")
        print("- Network connectivity issues")
        print("- API rate limits or quota exceeded")
        print("- Invalid model configuration")
        print("- API parameter validation errors (now shown directly from the API)")
        print("\nCheck your environment variables and Azure configuration.")

if __name__ == "__main__":
    asyncio.run(main())
