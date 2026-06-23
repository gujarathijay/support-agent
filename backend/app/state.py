"""
Shared state for the agent workflow.

This is the "clipboard" that all agents share. LangGraph passes this
state object to each node. Each agent reads what it needs and adds
its own results.

Key design decision: we use TypedDict (not Pydantic) because
LangGraph expects TypedDict for its state. Pydantic models are
used for the structured LLM outputs within each agent, but the
graph state itself is a TypedDict.

The flow:
  Input     → state has: customer_name, message, customer_id
  Triage    → adds: category, priority, sentiment, summary, triage_reasoning
  Research  → adds: research_findings
  Resolution→ adds: draft_response
  Guardrails→ adds: guardrail_passed, guardrail_violations, guardrail_summary
"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    """The shared state passed between all agents in the workflow.

    Each field is Optional because it starts empty and gets filled
    in by different agents at different stages.
    """

    # --- Input fields (set at the start) ---
    customer_name: str
    customer_id: str
    message: str

    # --- Triage agent fills these ---
    category: Optional[str]
    priority: Optional[str]
    sentiment: Optional[str]
    summary: Optional[str]
    triage_reasoning: Optional[str]

    # --- Research agent fills these ---
    research_findings: Optional[str]
    tools_called: Optional[list]

    # --- Resolution agent fills these ---
    draft_response: Optional[str]

    # --- Guardrails node fills these ---
    guardrail_passed: Optional[bool]
    guardrail_violations: Optional[list]
    guardrail_summary: Optional[str]