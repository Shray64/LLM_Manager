#!/usr/bin/env python3
"""
Independent Council Idea Generation Bot

A multi-LLM system where each LLM generates ideas independently:
1. Each LLM in the council maintains its own conversation history
2. Each LLM generates one response at a time
3. Each response is evaluated by the judge LLM
4. LLMs stop when their response scores below thresholds
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
    JUDGE_SYSTEM_PROMPT = prompts_module.JUDGE_SYSTEM_PROMPT
    COUNCIL_GENERATION_PROMPT_TEMPLATE = prompts_module.COUNCIL_GENERATION_PROMPT_TEMPLATE
else:
    raise ImportError(f"Could not find prompts.py at {_prompts_path}")

# Configuration
DEFAULT_MODELS = [
    "azure/o3",
    "azure/o1",
    "bedrock/claude-sonnet-3.7",
    "bedrock/claude-sonnet-4",
]

DEFAULT_JUDGE_MODEL = "bedrock/claude-sonnet-3.7"

# Default thresholds
DEFAULT_NOVELTY_THRESHOLD = 0.15
DEFAULT_COHERENCE_THRESHOLD = 15


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
        # Claude format: content[0].text (most common)
        if 'content' in response and isinstance(response['content'], list):
            if len(response['content']) > 0:
                content_item = response['content'][0]
                if isinstance(content_item, dict):
                    # Try 'text' key first
                    if 'text' in content_item:
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


class LLMState:
    """State for a single LLM in the council"""
    def __init__(self, model: str):
        self.model = model
        self.conversation_history: List[str] = []  # List of previous ideas generated
        self.is_active = True
        self.responses: List[Dict] = []  # List of {idea, novelty, coherence, reasoning, iteration}
    
    def add_response(self, idea: str, novelty: float, coherence: int, reasoning: str, iteration: int):
        """Add a response to history"""
        self.conversation_history.append(idea)
        self.responses.append({
            'idea': idea,
            'novelty': novelty,
            'coherence': coherence,
            'reasoning': reasoning,
            'iteration': iteration
        })
    
    def get_history_context(self) -> str:
        """Get formatted conversation history for prompt"""
        if not self.conversation_history:
            return "\n\nThis is your first response. Generate your first idea."
        
        history_text = "\n\nYour previous ideas:\n" + "\n\n".join(
            f"{i+1}. {idea}" for i, idea in enumerate(self.conversation_history)
        )
        return history_text


class IndependentCouncilBot:
    """Bot for independent council idea generation"""
    
    def __init__(self, llm_manager: LLMManager, judge_model: str = None, 
                 novelty_threshold: float = None, coherence_threshold: int = None):
        self.llm = llm_manager
        self.judge_model = judge_model or DEFAULT_JUDGE_MODEL
        self.novelty_threshold = novelty_threshold or DEFAULT_NOVELTY_THRESHOLD
        self.coherence_threshold = coherence_threshold or DEFAULT_COHERENCE_THRESHOLD
        
        # Callback for streaming updates (used by Streamlit)
        self.update_callback = None
    
    def set_update_callback(self, callback):
        """Set callback function for real-time updates"""
        self.update_callback = callback
    
    def _notify_update(self, model: str, iteration: int, idea: str, 
                      novelty: float, coherence: int, reasoning: str, is_active: bool):
        """Notify callback about updates"""
        if self.update_callback:
            self.update_callback({
                'model': model,
                'iteration': iteration,
                'idea': idea,
                'novelty': novelty,
                'coherence': coherence,
                'reasoning': reasoning,
                'is_active': is_active
            })
    
    async def generate_idea(self, question: str, llm_state: LLMState) -> Optional[str]:
        """Generate one idea from a single LLM"""
        if not llm_state.is_active:
            return None
        
        try:
            history_context = llm_state.get_history_context()
            prompt = COUNCIL_GENERATION_PROMPT_TEMPLATE.format(
                question=question,
                conversation_history=history_context
            )
            
            response = await self.llm.generate_async(
                prompt,
                model=llm_state.model,
                **_per_model_kwargs(llm_state.model)
            )
            
            response_text = extract_text_from_response(response)
            return response_text
        except Exception as e:
            print(f"  ⚠️  Error from {llm_state.model}: {e}")
            return None
    
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
    
    async def judge_evaluate(self, question: str, candidate_idea: str) -> Tuple[float, int, str]:
        """
        Judge evaluates the candidate idea for novelty and coherence.
        
        Returns:
            Tuple of (novelty_score, coherence_score, reasoning)
        """
        prompt = f"""Original Question: {question}

Candidate Idea:
{candidate_idea}

Evaluate this candidate idea and provide your scores."""
        
        try:
            judge_prompt = JUDGE_SYSTEM_PROMPT.format(
                novelty_threshold=self.novelty_threshold,
                coherence_threshold=self.coherence_threshold
            )
            full_prompt = f"{judge_prompt}\n\n{prompt}"
            response = await self.llm.generate_async(
                full_prompt,
                model=self.judge_model,
                **_per_model_kwargs(self.judge_model)
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
    
    async def process_llm_iteration(
        self, 
        question: str, 
        llm_state: LLMState, 
        iteration: int
    ) -> bool:
        """
        Process one iteration for a single LLM.
        
        Returns:
            True if LLM should continue, False if it should stop
        """
        if not llm_state.is_active:
            return False
        
        # Generate idea
        idea = await self.generate_idea(question, llm_state)
        if not idea:
            llm_state.is_active = False
            return False
        
        # Judge evaluates
        novelty, coherence, reasoning = await self.judge_evaluate(question, idea)
        
        # Check thresholds
        should_continue = novelty >= self.novelty_threshold and coherence >= self.coherence_threshold
        
        # Add to history
        llm_state.add_response(idea, novelty, coherence, reasoning, iteration)
        
        # Notify callback
        self._notify_update(
            llm_state.model, iteration, idea, novelty, coherence, reasoning, should_continue
        )
        
        # Update active status
        if not should_continue:
            llm_state.is_active = False
        
        return should_continue
    
    async def generate_ideas(
        self,
        question: str,
        models: List[str],
        max_iterations: int = 10
    ) -> Dict[str, LLMState]:
        """
        Main method to generate ideas from all LLMs independently.
        
        Args:
            question: The question to generate ideas for
            models: List of models to use
            max_iterations: Maximum number of iterations per LLM
            
        Returns:
            Dictionary mapping model names to their LLMState objects
        """
        # Initialize LLM states
        llm_states = {model: LLMState(model) for model in models}
        
        # Run iterations
        for iteration in range(1, max_iterations + 1):
            # Check if any LLM is still active
            active_llms = [state for state in llm_states.values() if state.is_active]
            if not active_llms:
                break
            
            # Process all active LLMs in parallel
            tasks = [
                self.process_llm_iteration(question, state, iteration)
                for state in active_llms
            ]
            
            await asyncio.gather(*tasks)
        
        return llm_states



