"""
Triage Agent — the first node in the workflow.

What it does:
  1. Reads the customer's message from shared state
  2. Calls Claude to classify it (category, priority, sentiment)
  3. Returns the classification fields → LangGraph merges them into state

This is a LangGraph "node" — just a function that takes state in
and returns a partial state update. LangGraph handles the merging.
"""

from langchain_anthropic import ChatAnthropic
from app.config import settings
from app.state import AgentState

# Create the LLM client
# In Phase 1 we used the raw Anthropic SDK. Now we use LangChain's
# wrapper because LangGraph works with LangChain's model interface.
# Under the hood, it makes the same API call.
llm = ChatAnthropic(
    model=settings.model_name,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)

TRIAGE_PROMPT = """You are a senior customer support triage specialist.

Analyze this support ticket and provide your classification.

Customer: {customer_name}
Message: {message}

Respond with EXACTLY this format (no extra text):
CATEGORY: <billing|technical|account|product|general>
PRIORITY: <low|medium|high|urgent>
SENTIMENT: <angry|frustrated|neutral|positive>
SUMMARY: <one sentence summary>
REASONING: <why you chose this category and priority>

Guidelines:
- urgent: service completely down, security breach, data loss
- high: significant functionality broken, billing errors with charges
- medium: feature not working as expected, general billing questions
- low: feature requests, general questions, how-to inquiries
"""


async def triage_node(state: AgentState) -> dict:
    """LangGraph node: classify the support ticket."""
    import time
    start = time.time()

    prompt = TRIAGE_PROMPT.format(
        customer_name=state["customer_name"],
        message=state["message"],
    )

    response = await llm.ainvoke(prompt)
    response_text = response.content

    result = _parse_triage_response(response_text)

    elapsed = time.time() - start
    print(f"  [Triage] {result['category']}/{result['priority']}/{result['sentiment']} ({elapsed:.1f}s)")

    return {
        "category": result["category"],
        "priority": result["priority"],
        "sentiment": result["sentiment"],
        "summary": result["summary"],
        "triage_reasoning": result["reasoning"],
    }


def _parse_triage_response(text: str) -> dict:
    """Parse Claude's triage response into a dictionary.

    Looks for lines like 'CATEGORY: billing' and extracts values.
    Falls back to defaults if parsing fails.
    """
    result = {
        "category": "general",
        "priority": "medium",
        "sentiment": "neutral",
        "summary": "Unable to parse summary",
        "reasoning": "Unable to parse reasoning",
    }

    for line in text.strip().split("\n"):
        line = line.strip()
        if line.upper().startswith("CATEGORY:"):
            result["category"] = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("PRIORITY:"):
            result["priority"] = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("SENTIMENT:"):
            result["sentiment"] = line.split(":", 1)[1].strip().lower()
        elif line.upper().startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("REASONING:"):
            result["reasoning"] = line.split(":", 1)[1].strip()

    return result