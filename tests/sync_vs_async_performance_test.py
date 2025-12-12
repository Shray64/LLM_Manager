#!/usr/bin/env python3
"""
Performance comparison test between sync and async calls across multiple models
Tests 3 models from Azure and Bedrock providers to compare performance
"""

import asyncio
import time
import sys
import os
from typing import List, Dict, Any
import statistics

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_manager import LLMManager

class PerformanceTest:
    def __init__(self):
        self.manager = LLMManager()
        self.test_prompt = "Explain the concept of artificial intelligence in 2-3 sentences. Focus on key characteristics and applications."
        
        # Select 3 models for testing (mix of Azure and Bedrock)
        self.test_models = self._select_test_models()
        
    def _select_test_models(self) -> List[str]:
        """Select 3 specific models for testing"""
        return [
            "azure/o3",
            "azure/gpt-5", 
            "bedrock/claude-sonnet-3.7"
        ]
    
    def _test_single_sync_call(self, model: str) -> Dict[str, Any]:
        """Test a single synchronous call"""
        start_time = time.time()
        try:
            response = self.manager.generate(
                self.test_prompt,
                model=model,
    
            )
            end_time = time.time()
            
            return {
                "success": True,
                "duration": end_time - start_time,
                "model": model,
                "response_length": len(str(response)),
                "error": None
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "duration": end_time - start_time,
                "model": model,
                "response_length": 0,
                "error": str(e)
            }
    
    async def _test_single_async_call(self, model: str) -> Dict[str, Any]:
        """Test a single asynchronous call"""
        start_time = time.time()
        try:
            response = await self.manager.generate_async(
                self.test_prompt,
                model=model,
        
            )
            end_time = time.time()
            
            return {
                "success": True,
                "duration": end_time - start_time,
                "model": model,
                "response_length": len(str(response)),
                "error": None
            }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "duration": end_time - start_time,
                "model": model,
                "response_length": 0,
                "error": str(e)
            }
    
    def test_sync_performance(self) -> Dict[str, Any]:
        """Test synchronous performance across all models"""
        print("🔄 Testing Synchronous Performance...")
        print("=" * 50)
        
        start_time = time.time()
        results = []
        
        for i, model in enumerate(self.test_models, 1):
            print(f"  [{i}/3] Testing {model}...")
            result = self._test_single_sync_call(model)
            results.append(result)
            
            if result["success"]:
                print(f"    ✅ {result['duration']:.2f}s - {result['response_length']} chars")
            else:
                print(f"    ❌ {result['duration']:.2f}s - Error: {result['error']}")
        
        total_time = time.time() - start_time
        
        return {
            "total_time": total_time,
            "results": results,
            "successful_calls": sum(1 for r in results if r["success"]),
            "failed_calls": sum(1 for r in results if not r["success"]),
            "avg_duration": statistics.mean([r["duration"] for r in results if r["success"]]) if any(r["success"] for r in results) else 0
        }
    
    async def test_async_performance(self) -> Dict[str, Any]:
        """Test asynchronous performance across all models"""
        print("\n⚡ Testing Asynchronous Performance...")
        print("=" * 50)
        
        start_time = time.time()
        
        # Create all async tasks
        tasks = [self._test_single_async_call(model) for model in self.test_models]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "duration": 0,
                    "model": self.test_models[i],
                    "response_length": 0,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        total_time = time.time() - start_time
        
        # Print results
        for i, result in enumerate(processed_results, 1):
            if result["success"]:
                print(f"  [{i}/3] ✅ {result['model']} - {result['duration']:.2f}s - {result['response_length']} chars")
            else:
                print(f"  [{i}/3] ❌ {result['model']} - {result['duration']:.2f}s - Error: {result['error']}")
        
        return {
            "total_time": total_time,
            "results": processed_results,
            "successful_calls": sum(1 for r in processed_results if r["success"]),
            "failed_calls": sum(1 for r in processed_results if not r["success"]),
            "avg_duration": statistics.mean([r["duration"] for r in processed_results if r["success"]]) if any(r["success"] for r in processed_results) else 0
        }
    
    async def test_all_models_together(self) -> Dict[str, Any]:
        """Test all models together on the same prompt asynchronously"""
        print("\n🤝 Testing All Models Together (Same Prompt)...")
        print("=" * 50)
        
        start_time = time.time()
        
        # Create all async tasks for the same prompt
        tasks = [self._test_single_async_call(model) for model in self.test_models]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "duration": 0,
                    "model": self.test_models[i],
                    "response_length": 0,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        total_time = time.time() - start_time
        
        # Print results
        print(f"Prompt: '{self.test_prompt[:50]}...'")
        print(f"Total time for all {len(self.test_models)} models: {total_time:.2f} seconds")
        print()
        
        for i, result in enumerate(processed_results, 1):
            if result["success"]:
                print(f"  [{i}/3] ✅ {result['model']} - {result['duration']:.2f}s - {result['response_length']} chars")
            else:
                print(f"  [{i}/3] ❌ {result['model']} - {result['duration']:.2f}s - Error: {result['error']}")
        
        return {
            "total_time": total_time,
            "results": processed_results,
            "successful_calls": sum(1 for r in processed_results if r["success"]),
            "failed_calls": sum(1 for r in processed_results if not r["success"]),
            "avg_duration": statistics.mean([r["duration"] for r in processed_results if r["success"]]) if any(r["success"] for r in processed_results) else 0
        }
    
    def print_performance_comparison(self, sync_results: Dict[str, Any], async_results: Dict[str, Any]):
        """Print detailed performance comparison"""
        print("\n📊 Performance Comparison Results")
        print("=" * 60)
        
        # Overall timing comparison
        print(f"🔄 Synchronous Total Time:  {sync_results['total_time']:.2f} seconds")
        print(f"⚡ Asynchronous Total Time: {async_results['total_time']:.2f} seconds")
        
        if sync_results['total_time'] > 0:
            speedup = sync_results['total_time'] / async_results['total_time']
            print(f"🚀 Speed Improvement:      {speedup:.2f}x faster with async")
        
        print(f"\n📈 Success Rates:")
        print(f"  Sync:  {sync_results['successful_calls']}/{len(self.test_models)} ({sync_results['successful_calls']/len(self.test_models)*100:.1f}%)")
        print(f"  Async: {async_results['successful_calls']}/{len(self.test_models)} ({async_results['successful_calls']/len(self.test_models)*100:.1f}%)")
        
        # Individual model comparison
        print(f"\n🔍 Individual Model Performance:")
        print(f"{'Model':<30} {'Sync (s)':<10} {'Async (s)':<10} {'Improvement':<12}")
        print("-" * 65)
        
        for i, model in enumerate(self.test_models):
            sync_result = sync_results['results'][i]
            async_result = async_results['results'][i]
            
            sync_time = f"{sync_result['duration']:.2f}" if sync_result['success'] else "Failed"
            async_time = f"{async_result['duration']:.2f}" if async_result['success'] else "Failed"
            
            if sync_result['success'] and async_result['success']:
                improvement = f"{sync_result['duration']/async_result['duration']:.2f}x"
            else:
                improvement = "N/A"
            
            print(f"{model:<30} {sync_time:<10} {async_time:<10} {improvement:<12}")
        
        # Client caching information
        print(f"\n💾 Client Caching Status:")
        for provider_name, provider in self.manager.providers.items():
            if hasattr(provider, '_clients') and hasattr(provider, '_async_clients'):
                sync_clients = len(provider._clients)
                async_clients = len(provider._async_clients)
                print(f"  {provider_name.capitalize()}: {sync_clients} sync clients, {async_clients} async clients")
    
    async def run_full_test(self):
        """Run the complete performance test"""
        print("🧪 LLM Manager Performance Test")
        print("=" * 60)
        print(f"Testing {len(self.test_models)} models:")
        for i, model in enumerate(self.test_models, 1):
            print(f"  {i}. {model}")
        print()
        
        # Test synchronous performance
        sync_results = self.test_sync_performance()
        
        # Test asynchronous performance
        async_results = await self.test_async_performance()
        
        # Test all models together on same prompt
        together_results = await self.test_all_models_together()
        
        # Print comparison
        self.print_performance_comparison(sync_results, async_results)
        
        # Cleanup
        print(f"\n🧹 Cleaning up cached clients...")
        for provider in self.manager.providers.values():
            if hasattr(provider, 'close_clients'):
                provider.close_clients()
        
        print(f"\n🎉 Performance test completed!")
        
        return {
            "sync_results": sync_results,
            "async_results": async_results,
            "together_results": together_results,
            "test_models": self.test_models
        }

async def main():
    """Main function to run the performance test"""
    try:
        test = PerformanceTest()
        results = await test.run_full_test()
        
        # Summary
        print(f"\n📋 Test Summary:")
        print(f"  Models tested: {len(results['test_models'])}")
        print(f"  Sync success rate: {results['sync_results']['successful_calls']}/{len(results['test_models'])}")
        print(f"  Async success rate: {results['async_results']['successful_calls']}/{len(results['test_models'])}")
        print(f"  Together success rate: {results['together_results']['successful_calls']}/{len(results['test_models'])}")
        
        if results['sync_results']['total_time'] > 0 and results['async_results']['total_time'] > 0:
            speedup = results['sync_results']['total_time'] / results['async_results']['total_time']
            print(f"  Overall speedup: {speedup:.2f}x")
        
        print(f"  Together test time: {results['together_results']['total_time']:.2f}s")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("Make sure your API keys are configured properly in the environment variables.")

if __name__ == "__main__":
    asyncio.run(main())
