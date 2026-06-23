"""
LLM client module — handles all communication with Claude.

This module wraps the Anthropic SDK and provides a clean interface
for the rest of our app. The key design decisions:

1. We use Claude's native tool use for structured output — instead
   of asking Claude to "return JSON" (which can fail), we define a
   tool whose input schema IS our Pydantic model. Claude is forced
   to return valid JSON matching that schema.

2. We use the async client because FastAPI is async — blocking calls
   would freeze the server for every request.

3. All LLM interaction is in this one file. If we switch models or
   providers later, we change this file and nothing else.
"""

import json
import anthropic
from app.config import settings
from app.models import TriageResult


# Create an async client (reused across requests — don't create one per call)
client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

# System prompt — tells Claude who it is and what it should do.
# This is separate from the user's message. Think of it as the
# "job description" for the agent.
TRIAGE_SYSTEM_PROMPT = """You are a senior customer support triage specialist.

Your job is to analyze incoming customer support tickets and classify them.
You must determine:
- The category (billing, technical, account, product, or general)
- The priority (low, medium, high, or urgent)
- The customer's sentiment (angry, frustrated, neutral, or positive)
- A brief summary of the issue
- Your reasoning for the classification

Guidelines:
- Urgent priority: service is completely down, security breach, or data loss
- High priority: significant functionality broken, billing errors charging wrong amounts
- Medium priority: feature not working as expected, general billing questions
- Low priority: feature requests, general questions, how-to inquiries
- Always assess sentiment based on the language and tone used
"""


async def triage_ticket(customer_name: str, message: str) -> TriageResult:
    """Send a support ticket to Claude and get back a structured triage result.

    We use Claude's tool use feature to get structured output:
    1. Define a "tool" whose input schema matches TriageResult
    2. Claude "calls" this tool, which forces it to produce valid JSON
    3. We parse the JSON into a TriageResult Pydantic model

    This is more reliable than prompting for JSON because the API
    constrains the output to match the schema exactly.
    """

    # Define the "tool" — this is our structured output schema
    # Claude sees this as a tool it can call, but we're really just
    # using it to force structured output
    tools = [
        {
            "name": "classify_ticket",
            "description": "Classify a customer support ticket with category, priority, sentiment, and summary.",
            "input_schema": TriageResult.model_json_schema(),
        }
    ]

    # Make the API call
    response = await client.messages.create(
        model=settings.model_name,
        max_tokens=settings.max_tokens,
        system=TRIAGE_SYSTEM_PROMPT,
        tools=tools,
        tool_choice={"type": "tool", "name": "classify_ticket"},  # Force tool use
        messages=[
            {
                "role": "user",
                "content": f"Please triage this support ticket.\n\nCustomer: {customer_name}\n\nMessage: {message}",
            }
        ],
    )

    # Extract the tool use result from the response
    # Claude's response contains content blocks — we want the tool_use block
    for block in response.content:
        if block.type == "tool_use":
            # Parse the tool input into our Pydantic model
            # This validates the data — if Claude returned something invalid,
            # Pydantic raises an error here
            return TriageResult.model_validate(block.input)

    # If we get here, something went wrong — Claude didn't use the tool
    raise ValueError("LLM did not return a tool use response")