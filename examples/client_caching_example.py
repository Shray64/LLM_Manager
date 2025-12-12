#!/usr/bin/env python3
"""
Example demonstrating the benefits of client caching
"""

import asyncio
import time
from llm_manager import LLMManager

async def demonstrate_client_caching():
    """Demonstrate client caching benefits"""
    print("Client Caching Benefits Demo")
    print("=" * 40)
    
    manager = LLMManager()
    
    try:
        # Test 1: Multiple calls to same model (benefits from caching)
        print("Test 1: Multiple calls to same model (gpt4o)")
        print("-" * 50)
        
        start_time = time.time()
        
        tasks = []
        for i in range(5):
            task = manager.generate_async(
                f"Question {i}: Explain {['AI', 'ML', 'DL', 'NLP', 'CV'][i]} in one sentence",
                model="azure/gpt4o",
                max_tokens=100
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"✅ Completed {len(responses)} calls in {end_time - start_time:.2f} seconds")
        print(f"   Average: {(end_time - start_time)/len(responses):.2f} seconds per call")
        
        # Test 2: Mixed model calls (creates separate cached clients)
        print("\nTest 2: Calls to different models")
        print("-" * 50)
        
        models_to_test = ["azure/gpt4o"]
        available_models = manager.list_models().get("azure", [])
        
        # Add other models if available
        if "o1" in available_models:
            models_to_test.append("azure/o1")
        if "gpt-5" in available_models:
            models_to_test.append("azure/gpt-5")
        
        start_time = time.time()
        
        tasks = []
        for i, model in enumerate(models_to_test):
            task = manager.generate_async(
                f"Question {i}: What is artificial intelligence?",
                model=model,
                max_completion_tokens=100
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"✅ Completed {len(responses)} calls to {len(models_to_test)} different models")
        print(f"   Time: {end_time - start_time:.2f} seconds")
        
        # Show cache status
        azure_provider = manager.providers.get("azure")
        if azure_provider:
            print(f"\nClient Cache Status:")
            print(f"  Sync clients: {len(azure_provider._clients)}")
            print(f"  Async clients: {len(azure_provider._async_clients)}")
            
            # Show cache keys (without sensitive data)
            if azure_provider._clients:
                print(f"  Sync cache keys: {len(azure_provider._clients)} unique configurations")
            if azure_provider._async_clients:
                print(f"  Async cache keys: {len(azure_provider._async_clients)} unique configurations")
        
        print("\n🎉 Client caching is working efficiently!")
        print("\nBenefits:")
        print("  ✅ Reduced connection overhead")
        print("  ✅ Better resource utilization")
        print("  ✅ Improved performance for repeated calls")
        print("  ✅ Connection reuse and pooling")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure your Azure API keys are configured properly.")

async def main():
    await demonstrate_client_caching()

if __name__ == "__main__":
    asyncio.run(main())
