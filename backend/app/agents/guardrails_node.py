"""
Guardrails Node — safety checkpoint in the workflow.

Now does TWO things:
  1. DETECT violations (PII, refund limits, banned phrases)
  2. AUTO-REDACT PII from the draft (emails, phones, SSNs)

The human reviewer gets a clean draft with [EMAIL REDACTED]
instead of real customer data. They can see in the guardrail
results that redaction happened, so they know to verify.
"""

from app.state import AgentState
from app.guardrails import run_all_guardrails, redact_pii


async def guardrails_node(state: AgentState) -> dict:
    """LangGraph node: check and clean the draft response."""

    draft = state.get("draft_response", "")

    if not draft:
        return {
            "guardrail_passed": False,
            "guardrail_violations": [{"type": "no_draft", "message": "No draft response to check", "severity": "high"}],
            "guardrail_summary": "No draft response was generated",
        }

    # Step 1: Detect all violations
    result = run_all_guardrails(draft)

    # Step 2: Auto-redact PII from the draft
    cleaned_draft, redaction_count = redact_pii(draft)

    if redaction_count > 0:
        print(f"  [Guardrails] Auto-redacted {redaction_count} PII item(s)")
        result["summary"] += f" | Auto-redacted {redaction_count} PII item(s)"

    # Log results
    print(f"  [Guardrails] {result['summary']}")
    if result["violations"]:
        for v in result["violations"]:
            print(f"    - [{v['severity'].upper()}] {v['message']}")

    return {
        "draft_response": cleaned_draft,  # overwrite with clean version
        "guardrail_passed": result["passed"],
        "guardrail_violations": result["violations"],
        "guardrail_summary": result["summary"],
    }