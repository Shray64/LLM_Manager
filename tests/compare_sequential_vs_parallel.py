#!/usr/bin/env python3
"""
Simple script to compare sequential vs parallel execution of LLM requests.
Tests 4 models: 2 Azure and 2 Bedrock models.
"""

import asyncio
import time
import sys
import os

# Add the src directory to the path so we can import llm_manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_manager import LLMManager

# Test prompt
PROMPT = "Describe an aspect of QCD using an analogy to, or contrast to, QED."

# Models to test (2 Azure, 2 Bedrock)
MODELS = [
    "azure/gpt4o",           # Azure model
    "azure/o1-mini",         # Azure model  
    "bedrock/claude-sonnet-3.7",  # Bedrock model
    "bedrock/claude-sonnet-4"     # Bedrock model
]

def _per_model_kwargs(model: str) -> dict:
    """Return provider/model specific kwargs.

    - For Bedrock Claude Sonnet 4, enable thinking with 8000 budget tokens.
    """
    if model == "bedrock/claude-sonnet-4":
        return {"thinking_tokens": 8000}
    return {}

def sequential_execution(llm_manager):
    """Execute requests sequentially"""
    print("🔄 Running SEQUENTIAL execution...")
    start_time = time.time()
    
    for i, model in enumerate(MODELS, 1):
        print(f"  [{i}/4] Calling {model}...")
        try:
            response = llm_manager.generate(PROMPT, model=model, **_per_model_kwargs(model))
            print(f"    ✅ Completed")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
    
    total_time = time.time() - start_time
    return total_time

async def parallel_execution(llm_manager):
    """Execute requests in parallel using async methods"""
    print("\n⚡ Running PARALLEL execution...")
    start_time = time.time()
    
    # Create async tasks for all models
    tasks = []
    for model in MODELS:
        task = asyncio.create_task(
            llm_manager.generate_async(PROMPT, model=model, **_per_model_kwargs(model))
        )
        tasks.append((model, task))
    
    # Wait for all tasks to complete
    for i, (model, task) in enumerate(tasks, 1):
        print(f"  [{i}/4] Waiting for {model}...")
        try:
            response = await task
            print(f"    ✅ Completed")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
    
    total_time = time.time() - start_time
    return total_time

def print_results(sequential_time, parallel_time):
    """Print comparison results"""
    print("\n" + "="*60)
    print("📊 EXECUTION TIME COMPARISON")
    print("="*60)
    
    print(f"\n⏱️  RESULTS:")
    print(f"   Sequential: {sequential_time:.2f}s")
    print(f"   Parallel:   {parallel_time:.2f}s")
    print(f"   Speedup:    {sequential_time/parallel_time:.2f}x faster")
    print(f"   Time saved: {sequential_time - parallel_time:.2f}s")

async def main():
    """Main function"""
    print("🚀 LLM Sequential vs Parallel Execution Comparison")
    print("="*60)
    print(f"Prompt: {PROMPT}")
    print(f"Models: {', '.join(MODELS)}")
    print("="*60)
    
    # Initialize LLM Manager
    try:
        llm_manager = LLMManager()
        print("✅ LLM Manager initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LLM Manager: {e}")
        return
    
    # Run sequential execution
    sequential_time = sequential_execution(llm_manager)
    
    # Run parallel execution
    parallel_time = await parallel_execution(llm_manager)
    
    # Print comparison results
    print_results(sequential_time, parallel_time)
    
    # Cleanup
    for provider in llm_manager.providers.values():
        if hasattr(provider, 'close_clients'):
            provider.close_clients()

if __name__ == "__main__":
    asyncio.run(main())
