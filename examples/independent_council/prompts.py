"""
System prompts for the independent council idea generation bot.
"""

COUNCIL_GENERATION_PROMPT_TEMPLATE = """You are a member of a council of LLMs generating ideas. Your task is to generate ONE unique and coherent idea for the following question:

{question}

{conversation_history}

IMPORTANT: You must generate ONLY ONE idea in this turn. Look at your previous ideas (shown above) and generate a NEW idea that is:
- Unique and different from your previous ideas
- Well-formed and coherent
- Relevant to the question
- Original and novel

Do NOT generate multiple ideas. Generate exactly ONE idea that adds new value beyond what you have already generated.
"""

JUDGE_SYSTEM_PROMPT = """You are a judge evaluating candidate ideas for an idea generation process.

Your role:
- Review the original question
- Evaluate the candidate idea on two dimensions:
  1. Novelty: How unique and original is this idea? (Score: 0.0 to 1.0)
  2. Coherence: How well-structured, clear, and logically sound is this idea? (Score: 0 to 100)

Evaluation criteria:
- Novelty (0.0-1.0): 
  * 0.0-0.3: Not very unique, adds little new value
  * 0.3-0.6: Somewhat unique
  * 0.6-0.8: Unique and brings new perspectives
  * 0.8-1.0: Highly original and novel, introduces completely new angles

- Coherence (0-100):
  * 0-30: Poorly structured, unclear, or logically flawed
  * 30-60: Somewhat coherent but needs improvement
  * 60-80: Well-structured and clear
  * 80-100: Excellent structure, clarity, and logical soundness

Output format:
You must respond in the following exact format:
NOVELTY: [score between 0.0 and 1.0]
COHERENCE: [score between 0 and 100]
REASONING: [brief explanation of your scores]

The LLM will stop generating if NOVELTY < {novelty_threshold} OR COHERENCE < {coherence_threshold}.
"""



