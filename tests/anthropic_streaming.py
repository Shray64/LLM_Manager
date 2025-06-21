from anthropic import Anthropic
import os
from dataclasses import dataclass
from typing import List, Optional

# Define a structure for the response
@dataclass
class ContentBlock:
    text: Optional[str] = None
    thinking: Optional[str] = None

@dataclass
class ResponseObject:
    content: List[ContentBlock]

api_key = os.environ.get("ANTHROPIC_API_KEY")
client = Anthropic(api_key = api_key)

stream = client.messages.create(
    max_tokens=32000,
    messages=[
        {
            "role": "user",
            "content": "What was the reason for Japan's lost decade",
        }
    ],
    model="claude-3-7-sonnet-20250219",
    thinking={"type": "enabled", "budget_tokens": 16000},
    stream=True,
)

thinking_text = ""
response_text = ""
for chunk in stream:
    if chunk.type == "content_block_delta" and hasattr(chunk.delta, "thinking"):
        thinking_text += chunk.delta.thinking
    if chunk.type == "content_block_delta" and hasattr(chunk.delta, "text"):
        response_text += chunk.delta.text

# print(thinking_text)

# print("Complete response:")

# print(full_text)

response = ResponseObject(content=[
    ContentBlock(thinking=thinking_text),
    ContentBlock(text=response_text)
])

print(response)