"""
Data models for the support resolution agent.

Every piece of data that enters or leaves our system has a Pydantic model.
This gives us:
  - Automatic validation (wrong types or missing fields → clear error)
  - Auto-generated API docs (FastAPI reads these models)
  - Structured LLM output (Claude fills in these exact fields)
  - Self-documenting code (the model IS the documentation)
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums — constrain fields to a fixed set of valid values
# ---------------------------------------------------------------------------

class Priority(str, Enum):
    """Ticket priority levels. Using an Enum means the LLM can ONLY
    return one of these four values — not 'super urgent' or 'kinda low'."""
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class Category(str, Enum):
    """Support ticket categories. These map to real team routing
    in a production support system."""
    billing = "billing"
    technical = "technical"
    account = "account"
    product = "product"
    general = "general"


class Sentiment(str, Enum):
    """Customer emotional state. Agents use this to adjust tone —
    a frustrated customer gets a different response than a calm one."""
    angry = "angry"
    frustrated = "frustrated"
    neutral = "neutral"
    positive = "positive"


# ---------------------------------------------------------------------------
# Request model — what the user sends IN to our API
# ---------------------------------------------------------------------------

class TicketRequest(BaseModel):
    """A customer support ticket submitted for triage.

    The Field descriptions are important — they show up in the
    auto-generated API docs AND help the LLM understand context.
    """
    customer_name: str = Field(
        description="Name of the customer submitting the ticket"
    )
    message: str = Field(
        description="The customer's support message"
    )
    customer_id: str = Field(
        default="unknown",
        description="Customer identifier for lookup"
    )


# ---------------------------------------------------------------------------
# Response model — what the LLM returns (structured output)
# ---------------------------------------------------------------------------

class TriageResult(BaseModel):
    """The triage agent's classification of a support ticket.

    This is the structured output we'll get from Claude.
    Every field has a description because Claude reads these
    descriptions to understand what to put in each field.
    """
    category: Category = Field(
        description="The primary support category this ticket belongs to"
    )
    priority: Priority = Field(
        description="How urgent this ticket is based on impact and severity"
    )
    sentiment: Sentiment = Field(
        description="The customer's emotional state based on their message"
    )
    summary: str = Field(
        description="A concise one-sentence summary of the customer's issue"
    )
    reasoning: str = Field(
        description="Brief explanation of why this category and priority were chosen"
    )


# ---------------------------------------------------------------------------
# API response wrapper — wraps the triage result with metadata
# ---------------------------------------------------------------------------

class TriageResponse(BaseModel):
    """Full API response returned to the frontend.
    Wraps the LLM's triage result with metadata about the request."""
    ticket: TicketRequest
    triage: TriageResult


# ---------------------------------------------------------------------------
# Phase 2: Full workflow response — includes all three agents' output
# ---------------------------------------------------------------------------

class WorkflowResponse(BaseModel):
    """Complete response from the multi-agent workflow.

    Contains the output of all agents:
    - Triage: classification (category, priority, sentiment)
    - Research: gathered context and findings
    - Resolution: draft customer response
    - Guardrails: safety check results
    """
    ticket_id: str = Field(default="", description="Ticket ID for approval tracking")
    status: str = Field(default="pending_approval", description="Ticket status")
    customer_name: str
    customer_id: str
    message: str
    category: str
    priority: str
    sentiment: str
    summary: str
    triage_reasoning: str
    research_findings: str
    tools_called: list = Field(default_factory=list)
    draft_response: str
    guardrail_passed: bool
    guardrail_violations: list
    guardrail_summary: str


# ---------------------------------------------------------------------------
# Phase 6: Approval request/response models
# ---------------------------------------------------------------------------

class ApproveRequest(BaseModel):
    """Request to approve a pending ticket."""
    reviewer: str = Field(default="human_reviewer", description="Who is approving")
    edited_response: Optional[str] = Field(default=None, description="Modified response text, if edited")
    note: Optional[str] = Field(default=None, description="Reviewer note")


class RejectRequest(BaseModel):
    """Request to reject a pending ticket."""
    reviewer: str = Field(default="human_reviewer", description="Who is rejecting")
    reason: str = Field(description="Why the draft was rejected")