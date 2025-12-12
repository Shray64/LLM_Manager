#!/usr/bin/env python3
"""
Simple test script for Azure async functionality
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_manager import LLMManager

async def test_azure_async():
    """Test Azure async functionality"""
    print("Testing Azure async functionality...")
    
    manager = LLMManager()
    
    try:
        # Test single async call
        print("Making async call...")
        response = await manager.generate_async(
            "What is Python programming?", 
            model="azure/gpt4o",
            max_tokens=100,
            temperature=0.7
        )
        print(f"✅ Async call successful: {response[:100]}...")
        
        # Test multiple concurrent async calls
        print("\nMaking multiple concurrent async calls...")
        tasks = [
            manager.generate_async("What is AI?", model="azure/gpt4o", max_tokens=50),
            manager.generate_async("What is ML?", model="azure/gpt4o", max_tokens=50),
            manager.generate_async("What is DL?", model="azure/gpt4o", max_tokens=50)
        ]
        
        responses = await asyncio.gather(*tasks)
        print(f"✅ Concurrent calls successful: {len(responses)} responses")
        for i, response in enumerate(responses):
            print(f"  Response {i+1}: {response[:50]}...")
        
        # Test reasoning model async call
        print("\nTesting reasoning model async call...")
        reasoning_response = await manager.generate_async(
            "Prove the Pythagorean theorem step by step",
            model="azure/gpt-5",
            max_completion_tokens=1000,
            reasoning_effort="medium"
        )
        
        if isinstance(reasoning_response, dict) and "thinking" in reasoning_response:
            print(f"✅ Reasoning model async call successful")
            print(f"  Thinking: {reasoning_response['thinking'][:100]}...")
            print(f"  Response: {reasoning_response['response'][:100]}...")
        else:
            print(f"✅ Reasoning model async call successful: {reasoning_response[:100]}...")
        
        print("\n🎉 All Azure async tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure your Azure API keys are configured properly.")

if __name__ == "__main__":
    asyncio.run(test_azure_async())
