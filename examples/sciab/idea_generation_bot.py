#!/usr/bin/env python3
"""
Idea Generation Bot

A multi-LLM system that generates unique ideas through an iterative process:
1. Council of LLMs generate responses to a question
2. Chairman LLM selects the most unique response
3. Judge LLM evaluates the selected response for novelty and coherence
4. Process continues until quality thresholds are not met
"""

import asyncio
import sys
import os
import time
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Add the src directory to the path so we can import llm_manager
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.join(_script_dir, '..', '..')
_src_dir = os.path.join(_project_root, 'src')
sys.path.insert(0, _src_dir)

from llm_manager import LLMManager

# Import prompts from the same directory
_prompts_path = os.path.join(_script_dir, 'prompts.py')
if os.path.exists(_prompts_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("prompts", _prompts_path)
    prompts_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prompts_module)
    CHAIRMAN_SYSTEM_PROMPT = prompts_module.CHAIRMAN_SYSTEM_PROMPT
    JUDGE_SYSTEM_PROMPT = prompts_module.JUDGE_SYSTEM_PROMPT
    COUNCIL_GENERATION_PROMPT_TEMPLATE = prompts_module.COUNCIL_GENERATION_PROMPT_TEMPLATE
else:
    raise ImportError(f"Could not find prompts.py at {_prompts_path}")

# Configuration
MODELS = [
    "azure/o3",
    "azure/o1",
    "bedrock/claude-sonnet-3.7",
    "bedrock/claude-sonnet-4",
]

CHAIRMAN_MODEL = "bedrock/claude-sonnet-3.7"
JUDGE_MODEL = "bedrock/claude-sonnet-3.7"

# Thresholds
NOVELTY_THRESHOLD = 0.15
COHERENCE_THRESHOLD = 15


def _per_model_kwargs(model: str) -> dict:
    """Return provider/model specific kwargs."""
    if model == "bedrock/claude-sonnet-4":
        return {
            "max_tokens": 20000,
            "temperature": 1,
            "thinking_tokens": 8000
        }
    return {}


def extract_text_from_response(response) -> str:
    """
    Extract text content from various response object types.
    
    Handles:
    - Azure OpenAI responses (Pydantic models)
    - Bedrock responses (dict)
    - Other response formats
    """
    # If it's already a string, return it
    if isinstance(response, str):
        return response
    
    # Azure OpenAI responses with output (reasoning models)
    if hasattr(response, 'output') and response.output:
        if len(response.output) >= 2:
            return response.output[1].content[0].text
        elif len(response.output) >= 1:
            if hasattr(response.output[0], 'content') and response.output[0].content:
                return response.output[0].content[0].text
    
    # Azure OpenAI chat completions
    if hasattr(response, 'choices') and response.choices:
        if hasattr(response.choices[0], 'message'):
            content = response.choices[0].message.content
            if content:
                return content
    
    # Bedrock responses (dict format)
    if isinstance(response, dict):
        # Claude format: content array with potentially multiple items
        # Claude Sonnet 4 may have: [{'type': 'thinking', 'thinking': '...'}, {'type': 'text', 'text': '...'}]
        if 'content' in response and isinstance(response['content'], list):
            # Iterate through content items to find the text block
            # Skip thinking blocks and find the first text block
            for content_item in response['content']:
                if isinstance(content_item, dict):
                    # Check if this is a text block (not a thinking block)
                    if content_item.get('type') == 'text' and 'text' in content_item:
                        return content_item['text']
                    # Fallback: if no type specified but has 'text' key, use it
                    elif 'text' in content_item and content_item.get('type') != 'thinking':
                        return content_item['text']
                    # Try nested content structure
                    if 'content' in content_item and isinstance(content_item['content'], list):
                        if len(content_item['content']) > 0:
                            nested = content_item['content'][0]
                            if isinstance(nested, dict) and 'text' in nested:
                                return nested['text']
        
        # Alternative Bedrock format
        if 'outputs' in response:
            outputs = response['outputs']
            if isinstance(outputs, list) and len(outputs) > 0:
                output = outputs[0]
                if isinstance(output, dict) and 'text' in output:
                    return output['text']
        
        # Try direct 'text' key
        if 'text' in response:
            return response['text']
    
    # Fallback: try to convert to string
    return str(response)


class IdeaGenerationBot:
    """Main bot class for idea generation process"""
    
    def __init__(self, llm_manager: LLMManager, output_file: Optional[str] = None):
        self.llm = llm_manager
        self.selected_ideas: List[str] = []
        self.iteration_count = 0
        
        # Set up output file
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"idea_generation_output_{timestamp}.md"
        
        self.output_file = output_file
        self.output_fp = None
        
    def _write_to_file(self, text: str, also_print: bool = False):
        """Write text to output file and optionally print to console"""
        if self.output_fp is None:
            self.output_fp = open(self.output_file, 'w', encoding='utf-8')
        
        self.output_fp.write(text)
        self.output_fp.flush()  # Ensure it's written immediately
        
        if also_print:
            print(text, end='')
    
    def _close_file(self):
        """Close the output file"""
        if self.output_fp:
            self.output_fp.close()
            self.output_fp = None
        
    async def generate_council_responses(
        self, 
        question: str, 
        models: List[str],
        parallel: bool = True
    ) -> List[Tuple[str, str]]:
        """
        Generate responses from all council LLMs.
        
        Returns:
            List of tuples (model_name, response)
        """
        # Build context about selected ideas
        if self.selected_ideas:
            selected_ideas_context = "\n\nIdeas already selected by the council:\n" + "\n\n".join(
                f"{i+1}. {idea}" for i, idea in enumerate(self.selected_ideas)
            )
        else:
            selected_ideas_context = "\n\nNo ideas have been selected yet. This is the first iteration."
        
        async def call_model(model: str):
            try:
                prompt = COUNCIL_GENERATION_PROMPT_TEMPLATE.format(
                    question=question,
                    selected_ideas_context=selected_ideas_context
                )
                response = await self.llm.generate_async(
                    prompt,
                    model=model,
                    **_per_model_kwargs(model)
                )
                # Extract text from response object
                response_text = extract_text_from_response(response)
                return model, response_text, None
            except Exception as e:
                return model, None, e
        
        if parallel:
            tasks = [call_model(model) for model in models]
            results = await asyncio.gather(*tasks)
        else:
            results = []
            for model in models:
                result = await call_model(model)
                results.append(result)
        
        responses = []
        for model, response, error in results:
            if error:
                print(f"  ⚠️  Error from {model}: {error}")
            elif response:
                responses.append((model, response))
        
        return responses
    
    def _parse_chairman_selection(self, response: str) -> Tuple[Optional[int], str]:
        """
        Parse the chairman's response to extract the selected index.
        
        Returns:
            Tuple of (index, reason) or (None, reason) if parsing fails
        """
        # Try to find "Index: X" pattern
        index_match = re.search(r'Index:\s*(\d+)', response, re.IGNORECASE)
        if index_match:
            index = int(index_match.group(1))
            reason = response
            return index, reason
        
        # Try to find just a number at the start
        number_match = re.search(r'^\s*(\d+)', response)
        if number_match:
            index = int(number_match.group(1))
            reason = response
            return index, reason
        
        # If no clear index found, try to extract from context
        # Look for patterns like "response 2", "option 3", etc.
        alt_match = re.search(r'(?:response|option|idea|choice)\s+(\d+)', response, re.IGNORECASE)
        if alt_match:
            index = int(alt_match.group(1))
            reason = response
            return index, reason
        
        return None, response
    
    async def chairman_select(
        self, 
        question: str,
        council_responses: List[Tuple[str, str]]
    ) -> Tuple[Optional[int], str, str]:
        """
        Chairman selects the most unique response from council.
        
        Returns:
            Tuple of (selected_index, selected_response, reason)
        """
        if not council_responses:
            return None, "", "No responses to select from"
        
        # Build the prompt for chairman
        responses_text = "\n\n".join(
            f"[{i}] Model: {model}\nResponse: {response}"
            for i, (model, response) in enumerate(council_responses)
        )
        
        selected_text = ""
        if self.selected_ideas:
            selected_text = "\n\nIdeas already selected:\n" + "\n\n".join(
                f"- {idea}" for idea in self.selected_ideas
            )
        
        prompt = f"""Original Question: {question}

Council Responses:
{responses_text}
{selected_text}

Select the response (by index) that is the MOST UNIQUE compared to the ideas already selected."""
        
        try:
            # Use system prompt if supported, otherwise prepend to user message
            full_prompt = f"{CHAIRMAN_SYSTEM_PROMPT}\n\n{prompt}"
            response = await self.llm.generate_async(
                full_prompt,
                model=CHAIRMAN_MODEL,
                **_per_model_kwargs(CHAIRMAN_MODEL)
            )
            
            # Extract text from response object
            response_text = extract_text_from_response(response)
            index, reason = self._parse_chairman_selection(response_text)
            
            if index is not None and 0 <= index < len(council_responses):
                selected_model, selected_response = council_responses[index]
                return index, selected_response, reason
            else:
                # Fallback: select first response if parsing failed
                print(f"  ⚠️  Could not parse chairman selection, defaulting to first response")
                print(f"  Chairman response: {response_text[:200]}...")
                return 0, council_responses[0][1], reason
                
        except Exception as e:
            print(f"  ❌ Error in chairman selection: {e}")
            # Fallback to first response
            return 0, council_responses[0][1], f"Error: {e}"
    
    def _parse_judge_scores(self, response: str) -> Tuple[Optional[float], Optional[int], str]:
        """
        Parse judge's response to extract novelty and coherence scores.
        
        Returns:
            Tuple of (novelty_score, coherence_score, reasoning)
        """
        novelty = None
        coherence = None
        reasoning = response
        
        # Try to find NOVELTY: X.X pattern
        novelty_match = re.search(r'NOVELTY:\s*([\d.]+)', response, re.IGNORECASE)
        if novelty_match:
            try:
                novelty = float(novelty_match.group(1))
            except ValueError:
                pass
        
        # Try to find COHERENCE: XX pattern
        coherence_match = re.search(r'COHERENCE:\s*(\d+)', response, re.IGNORECASE)
        if coherence_match:
            try:
                coherence = int(coherence_match.group(1))
            except ValueError:
                pass
        
        # Try to find REASONING: section
        reasoning_match = re.search(r'REASONING:\s*(.+?)(?:\n\n|\Z)', response, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            reasoning = reasoning_match.group(1).strip()
        
        return novelty, coherence, reasoning
    
    async def judge_evaluate(
        self,
        question: str,
        candidate_idea: str
    ) -> Tuple[float, int, str]:
        """
        Judge evaluates the candidate idea for novelty and coherence.
        
        Returns:
            Tuple of (novelty_score, coherence_score, reasoning)
        """
        selected_text = ""
        if self.selected_ideas:
            selected_text = "\n\nIdeas already selected:\n" + "\n\n".join(
                f"- {idea}" for idea in self.selected_ideas
            )
        
        prompt = f"""Original Question: {question}
{selected_text}

Candidate Idea (selected by chairman):
{candidate_idea}

Evaluate this candidate idea and provide your scores."""
        
        try:
            full_prompt = f"{JUDGE_SYSTEM_PROMPT}\n\n{prompt}"
            response = await self.llm.generate_async(
                full_prompt,
                model=JUDGE_MODEL,
                **_per_model_kwargs(JUDGE_MODEL)
            )
            
            # Extract text from response object
            response_text = extract_text_from_response(response)
            novelty, coherence, reasoning = self._parse_judge_scores(response_text)
            
            # Default values if parsing failed
            if novelty is None:
                print(f"  ⚠️  Could not parse novelty score, defaulting to 0.5")
                novelty = 0.5
            if coherence is None:
                print(f"  ⚠️  Could not parse coherence score, defaulting to 50")
                coherence = 50
            
            return novelty, coherence, reasoning
            
        except Exception as e:
            print(f"  ❌ Error in judge evaluation: {e}")
            # Return default scores that will likely fail thresholds
            return 0.0, 0, f"Error: {e}"
    
    async def run_iteration(
        self,
        question: str,
        models: List[str],
        parallel: bool = True
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        Run one iteration of the idea generation process.
        
        Returns:
            Tuple of (should_continue, selected_idea, metadata)
        """
        self.iteration_count += 1
        
        # Terminal progress
        print(f"\n[Iteration {self.iteration_count}] Processing...", end='', flush=True)
        
        # File output - Start iteration section
        self._write_to_file(f"\n\n{'='*80}\n")
        self._write_to_file(f"# Iteration {self.iteration_count}\n")
        self._write_to_file(f"{'='*80}\n\n")
        
        # Step 1: Generate council responses
        print(" [Step 1: Council]", end='', flush=True)
        self._write_to_file(f"## Step 1: Council Response Generation\n\n")
        self._write_to_file(f"**Models:** {', '.join(models)}\n")
        self._write_to_file(f"**Mode:** {'Parallel' if parallel else 'Sequential'}\n\n")
        
        start_time = time.time()
        council_responses = await self.generate_council_responses(question, models, parallel)
        council_time = time.time() - start_time
        
        if not council_responses:
            self._write_to_file(f"❌ **Error:** No valid responses generated. Stopping.\n\n")
            print(" ❌")
            return False, None, {"error": "No council responses"}
        
        self._write_to_file(f"✅ Generated {len(council_responses)} responses in {council_time:.2f}s\n\n")
        
        # Write all council responses to file
        self._write_to_file(f"### Council Responses\n\n")
        for i, (model, response) in enumerate(council_responses):
            self._write_to_file(f"#### Response {i}: {model}\n\n")
            self._write_to_file(f"```\n{response}\n```\n\n")
            self._write_to_file(f"---\n\n")
        
        # Step 2: Chairman selects most unique
        print(" [Step 2: Chairman]", end='', flush=True)
        self._write_to_file(f"## Step 2: Chairman Selection\n\n")
        self._write_to_file(f"**Model:** {CHAIRMAN_MODEL}\n\n")
        
        start_time = time.time()
        selected_index, selected_idea, chairman_reason = await self.chairman_select(
            question, council_responses
        )
        chairman_time = time.time() - start_time
        
        selected_model = council_responses[selected_index][0]
        self._write_to_file(f"✅ Selected response **#{selected_index}** from **{selected_model}** in {chairman_time:.2f}s\n\n")
        self._write_to_file(f"**Selection Reasoning:**\n\n{chairman_reason}\n\n")
        
        # Write selected response clearly
        self._write_to_file(f"### 🎯 Chairman's Selected Response\n\n")
        self._write_to_file(f"**Model:** {selected_model}  \n")
        self._write_to_file(f"**Index:** {selected_index}\n\n")
        self._write_to_file(f"```\n{selected_idea}\n```\n\n")
        
        # Step 3: Judge evaluates
        print(" [Step 3: Judge]", end='', flush=True)
        self._write_to_file(f"## Step 3: Judge Evaluation\n\n")
        self._write_to_file(f"**Model:** {JUDGE_MODEL}\n\n")
        
        start_time = time.time()
        novelty, coherence, judge_reasoning = await self.judge_evaluate(question, selected_idea)
        judge_time = time.time() - start_time
        
        self._write_to_file(f"✅ Evaluation complete in {judge_time:.2f}s\n\n")
        self._write_to_file(f"### Scores\n\n")
        self._write_to_file(f"- **Novelty:** {novelty:.3f} / 1.0 (threshold: {NOVELTY_THRESHOLD})  \n")
        self._write_to_file(f"- **Coherence:** {coherence} / 100 (threshold: {COHERENCE_THRESHOLD})  \n\n")
        self._write_to_file(f"**Judge Reasoning:**\n\n{judge_reasoning}\n\n")
        
        # Check thresholds
        should_continue = novelty >= NOVELTY_THRESHOLD and coherence >= COHERENCE_THRESHOLD
        
        metadata = {
            "iteration": self.iteration_count,
            "council_responses_count": len(council_responses),
            "selected_index": selected_index,
            "novelty": novelty,
            "coherence": coherence,
            "chairman_reason": chairman_reason,
            "judge_reasoning": judge_reasoning,
            "timings": {
                "council": council_time,
                "chairman": chairman_time,
                "judge": judge_time
            }
        }
        
        if should_continue:
            self.selected_ideas.append(selected_idea)
            self._write_to_file(f"### ✅ Result: ACCEPTED\n\n")
            self._write_to_file(f"The idea meets both thresholds and has been added to the collection.\n\n")
            print(" ✅ Accepted")
        else:
            self._write_to_file(f"### ❌ Result: REJECTED\n\n")
            reasons = []
            if novelty < NOVELTY_THRESHOLD:
                reasons.append(f"Novelty ({novelty:.3f}) below threshold ({NOVELTY_THRESHOLD})")
            if coherence < COHERENCE_THRESHOLD:
                reasons.append(f"Coherence ({coherence}) below threshold ({COHERENCE_THRESHOLD})")
            self._write_to_file(f"**Reasons:**\n\n")
            for reason in reasons:
                self._write_to_file(f"- {reason}\n")
            self._write_to_file(f"\n")
            print(" ❌ Rejected")
        
        return should_continue, selected_idea if should_continue else None, metadata
    
    async def generate_ideas(
        self,
        question: str,
        models: List[str] = None,
        parallel: bool = True,
        max_iterations: int = 10
    ) -> List[str]:
        """
        Main method to generate ideas iteratively.
        
        Args:
            question: The question to generate ideas for
            models: List of models to use (defaults to MODELS)
            parallel: Whether to run council generation in parallel
            max_iterations: Maximum number of iterations
            
        Returns:
            List of selected ideas
        """
        if models is None:
            models = MODELS
        
        # Write header to file
        self._write_to_file(f"# Idea Generation Bot Output\n\n")
        self._write_to_file(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        self._write_to_file(f"## Configuration\n\n")
        self._write_to_file(f"- **Question:** {question}\n")
        self._write_to_file(f"- **Council Models:** {', '.join(models)}\n")
        self._write_to_file(f"- **Chairman Model:** {CHAIRMAN_MODEL}\n")
        self._write_to_file(f"- **Judge Model:** {JUDGE_MODEL}\n")
        self._write_to_file(f"- **Mode:** {'Parallel' if parallel else 'Sequential'}\n")
        self._write_to_file(f"- **Novelty Threshold:** {NOVELTY_THRESHOLD}\n")
        self._write_to_file(f"- **Coherence Threshold:** {COHERENCE_THRESHOLD}\n")
        self._write_to_file(f"- **Max Iterations:** {max_iterations}\n\n")
        self._write_to_file(f"{'='*80}\n\n")
        
        # Terminal output
        print(f"\n{'='*60}")
        print(f"Idea Generation Bot")
        print(f"{'='*60}")
        print(f"Question: {question}")
        print(f"Output file: {self.output_file}")
        print(f"{'='*60}")
        
        self.selected_ideas = []
        self.iteration_count = 0
        
        iteration = 0
        while iteration < max_iterations:
            should_continue, idea, metadata = await self.run_iteration(
                question, models, parallel
            )
            
            if not should_continue:
                break
            
            iteration += 1
        
        if iteration >= max_iterations:
            self._write_to_file(f"\n⚠️ **Note:** Reached maximum iterations ({max_iterations})\n\n")
            print(f"\n⚠️  Reached maximum iterations ({max_iterations})")
        
        # Write final summary to file
        self._write_to_file(f"\n{'='*80}\n\n")
        self._write_to_file(f"# Final Summary\n\n")
        self._write_to_file(f"- **Total Ideas Generated:** {len(self.selected_ideas)}\n")
        self._write_to_file(f"- **Total Iterations:** {self.iteration_count}\n\n")
        
        if self.selected_ideas:
            self._write_to_file(f"## All Selected Ideas\n\n")
            for i, idea in enumerate(self.selected_ideas, 1):
                self._write_to_file(f"### Idea {i}\n\n")
                self._write_to_file(f"```\n{idea}\n```\n\n")
                self._write_to_file(f"---\n\n")
        
        # Terminal summary
        print(f"\n{'='*60}")
        print(f"Final Results")
        print(f"{'='*60}")
        print(f"Total ideas generated: {len(self.selected_ideas)}")
        print(f"Total iterations: {self.iteration_count}")
        print(f"\n📄 Detailed output saved to: {self.output_file}")
        
        # Close file
        self._close_file()
        
        return self.selected_ideas


async def main():
    """Main entry point"""
    question = input("Enter your question: ").strip()
    if not question:
        print("Empty question, exiting.")
        return
    
    mode = input("Run council generation in parallel? [y/n]: ").strip().lower()
    parallel = mode in ("y", "yes")
    
    max_iterations = input("Maximum iterations (default 10): ").strip()
    try:
        max_iterations = int(max_iterations) if max_iterations else 10
    except ValueError:
        max_iterations = 10
    
    try:
        llm = LLMManager()
    except Exception as e:
        print(f"Failed to init LLMManager: {e}")
        return
    
    # Create output file in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(script_dir, f"idea_generation_output_{timestamp}.md")
    
    bot = IdeaGenerationBot(llm, output_file=output_file)
    
    try:
        ideas = await bot.generate_ideas(
            question=question,
            models=MODELS,
            parallel=parallel,
            max_iterations=max_iterations
        )
        
        print(f"\n{'='*60}")
        print(f"Summary")
        print(f"{'='*60}")
        print(f"Total ideas: {len(ideas)}")
        print(f"📄 Full details saved to: {output_file}")
        
    finally:
        # Cleanup
        for provider in llm.providers.values():
            if hasattr(provider, 'close_clients'):
                provider.close_clients()


if __name__ == "__main__":
    asyncio.run(main())

