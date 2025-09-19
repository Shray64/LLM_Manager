#!/usr/bin/env python3
"""
Test script to demonstrate client caching performance improvement
"""

import asyncio
import time
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_manager import LLMManager

async def test_client_caching():
    """Test that client caching works and improves performance"""
    print("Testing client caching performance...")
    
    manager = LLMManager()
    
    try:
        # Test multiple calls to the same model (should reuse client)
        print("Making multiple calls to the same model...")
        
        start_time = time.time()
        
        # Make several calls to the same model
        tasks = []
        for i in range(5):
            task = manager.generate_async(
                f"Question {i}: What is Python programming?", 
                model="azure/gpt4o",
                max_tokens=100
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"✅ Made {len(responses)} calls in {end_time - start_time:.2f} seconds")
        print(f"Average time per call: {(end_time - start_time)/len(responses):.2f} seconds")
        
        # Test calls to different models (should create separate clients)
        print("\nMaking calls to different models...")
        
        start_time = time.time()
        
        # Test different models if available
        models_to_test = ["azure/gpt4o"]
        if "azure/o1" in manager.list_models().get("azure", []):
            models_to_test.append("azure/o1")
        if "azure/gpt-5" in manager.list_models().get("azure", []):
            models_to_test.append("azure/gpt-5")
        
        tasks = []
        for i, model in enumerate(models_to_test):
            task = manager.generate_async(
                f"Question {i}: What is AI?", 
                model=model,
                max_tokens=100
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"✅ Made {len(responses)} calls to {len(models_to_test)} different models in {end_time - start_time:.2f} seconds")
        
        # Check that clients are cached
        azure_provider = manager.providers.get("azure")
        if azure_provider:
            print(f"\nClient cache status:")
            print(f"  Sync clients cached: {len(azure_provider._clients)}")
            print(f"  Async clients cached: {len(azure_provider._async_clients)}")
        
        print("\n🎉 Client caching test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure your Azure API keys are configured properly.")

def test_sync_client_caching():
    """Test sync client caching"""
    print("\nTesting sync client caching...")
    
    manager = LLMManager()
    
    try:
        start_time = time.time()
        
        # Make several sync calls
        responses = []
        for i in range(3):
            response = manager.generate(
                f"Question {i}: What is machine learning?", 
                model="azure/gpt4o",
                max_tokens=100
            )
            responses.append(response)
        
        end_time = time.time()
        
        print(f"✅ Made {len(responses)} sync calls in {end_time - start_time:.2f} seconds")
        
        # Check that clients are cached
        azure_provider = manager.providers.get("azure")
        if azure_provider:
            print(f"  Sync clients cached: {len(azure_provider._clients)}")
        
    except Exception as e:
        print(f"❌ Sync test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_client_caching())
    test_sync_client_caching()
