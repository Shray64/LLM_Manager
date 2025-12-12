#!/usr/bin/env python3
import asyncio
import sys
import os
import time

# Add the src directory to the path so we can import llm_manager
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_manager import LLMManager

MODELS = [
    "azure/o3",
    "azure/o1",
    "bedrock/claude-sonnet-3.7",
    "bedrock/claude-sonnet-4",
]

def _per_model_kwargs(model: str) -> dict:
    """Return provider/model specific kwargs.

    For Bedrock Claude Sonnet 4, enable thinking with 8000 budget tokens.
    """
    if model == "bedrock/claude-sonnet-4":
        return {"max_tokens": 20000,
        "temperature":1,
        "thinking_tokens": 8000}
    return {}

def print_header(prompt, mode):
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print(f"Mode: {'Sequential' if mode == 's' else 'Parallel'}")
    print(f"Models: {', '.join(MODELS)}")
    print("=" * 60)

def run_sequential(llm, prompt):
    print("Running sequentially...\n")
    start = time.time()
    for i, model in enumerate(MODELS, 1):
        print(f"[{i}/{len(MODELS)}] {model}:")
        t0 = time.time()
        try:
            resp = llm.generate(prompt, model=model, **_per_model_kwargs(model))
            dt = time.time() - t0
            print(f"  ✅ Done in {dt:.2f}s")
            print("  ----- response begin -----")
            print(resp)
            print("  ------ response end ------\n")
        except Exception as e:
            dt = time.time() - t0
            print(f"  ❌ Error in {dt:.2f}s: {e}\n")
    total = time.time() - start
    print(f"Total time (sequential): {total:.2f}s")

async def call_model_async(llm, model, prompt):
    t0 = time.time()
    try:
        resp = await llm.generate_async(prompt, model=model, **_per_model_kwargs(model))
        return model, resp, None, time.time() - t0
    except Exception as e:
        return model, None, e, time.time() - t0

async def run_parallel(llm, prompt):
    print("Running in parallel...\n")
    start = time.time()
    tasks = [asyncio.create_task(call_model_async(llm, m, prompt)) for m in MODELS]
    for fut in asyncio.as_completed(tasks):
        model, resp, err, dt = await fut
        if err:
            print(f"[{model}] ❌ Error in {dt:.2f}s: {err}\n")
        else:
            print(f"[{model}] ✅ Done in {dt:.2f}s")
            print("----- response begin -----")
            print(resp)
            print("------ response end ------\n")
    total = time.time() - start
    print(f"Total time (parallel): {total:.2f}s")

def main():
    prompt = input("Enter your prompt: ").strip()
    if not prompt:
        print("Empty prompt, exiting.")
        return

    mode = input("Run sequentially or parallel? [s/p]: ").strip().lower()
    if mode not in ("s", "p"):
        print("Invalid choice. Use 's' or 'p'.")
        return

    try:
        llm = LLMManager()
    except Exception as e:
        print(f"Failed to init LLMManager: {e}")
        return

    print_header(prompt, mode)

    try:
        if mode == "s":
            run_sequential(llm, prompt)
        else:
            asyncio.run(run_parallel(llm, prompt))
    finally:
        for provider in llm.providers.values():
            if hasattr(provider, 'close_clients'):
                provider.close_clients()

if __name__ == "__main__":
    main()