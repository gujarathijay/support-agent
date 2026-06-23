"""
Resolution Agent — the third and final node in the workflow.

What it does:
  1. Reads EVERYTHING from state (triage + research results)
  2. Calls Claude to draft a customer-facing response
  3. Returns draft_response → LangGraph merges into state

This agent has the most context because it runs last — it sees
the original message, the triage classification, AND the research
findings. It uses all of that to write an appropriate response.

In Phase 6, the draft goes to a human for approval before sending.
"""

from langchain_anthropic import ChatAnthropic
from app.config import settings
from app.state import AgentState

llm = ChatAnthropic(
    model=settings.model_name,
    api_key=settings.anthropic_api_key,
    max_tokens=settings.max_tokens,
)

RESOLUTION_PROMPT = """You are a senior customer support agent drafting a response.

Ticket information:
- Customer name: {customer_name}
- Category: {category}
- Priority: {priority}
- Customer sentiment: {sentiment}
- Issue summary: {summary}
- Original message: {message}

Research findings:
{research_findings}

Draft a professional, empathetic customer response that:
1. Acknowledges their issue and shows understanding
2. Addresses their specific problem based on the research
3. Provides a clear solution or next steps
4. Matches the appropriate tone for their sentiment
   - If angry/frustrated: extra empathetic, apologize, show urgency
   - If neutral: professional and helpful
   - If positive: warm and appreciative
5. Keeps it concise — no more than 3-4 short paragraphs

Write ONLY the response text. Do not include subject lines,
headers, or metadata. Start directly with the greeting.
"""


async def resolution_node(state: AgentState) -> dict:
    """LangGraph node: draft the customer response."""
    import time
    start = time.time()

    prompt = RESOLUTION_PROMPT.format(
        customer_name=state["customer_name"],
        message=state["message"],
        category=state.get("category", "general"),
        priority=state.get("priority", "medium"),
        sentiment=state.get("sentiment", "neutral"),
        summary=state.get("summary", "No summary available"),
        research_findings=state.get("research_findings", "No research available"),
    )

    response = await llm.ainvoke(prompt)

    elapsed = time.time() - start
    print(f"  [Resolution] Draft generated ({elapsed:.1f}s)")

    return {
        "draft_response": response.content,
    }