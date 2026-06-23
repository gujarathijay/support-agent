"""
Test the full workflow including human-in-the-loop approval.

Flow:
  1. Submit ticket → agents run → draft queued as pending
  2. List pending tickets → see the draft
  3. Approve (or edit, or reject) → ticket finalized
"""

import httpx
import time

BASE_URL = "http://localhost:8000"
TIMEOUT = 120


def submit_ticket(customer_name: str, customer_id: str, message: str) -> dict:
    """Submit a ticket and get back the draft with a ticket ID."""
    print("=" * 60)
    print(f"STEP 1: Submit ticket")
    print(f"  Customer: {customer_name} ({customer_id})")
    print(f"  Message:  {message[:60]}...")
    print("=" * 60)

    start = time.time()
    response = httpx.post(
        f"{BASE_URL}/resolve",
        json={
            "customer_name": customer_name,
            "message": message,
            "customer_id": customer_id,
        },
        timeout=TIMEOUT,
    )
    elapsed = time.time() - start

    result = response.json()

    print(f"\n  Ticket ID:  {result['ticket_id']}")
    print(f"  Status:     {result['status']}")
    print(f"  Category:   {result['category']}")
    print(f"  Priority:   {result['priority']}")
    print(f"  Guardrails: {'PASSED' if result['guardrail_passed'] else 'FAILED'}")
    print(f"  Time:       {elapsed:.1f}s")
    print(f"\n  Draft response (first 200 chars):")
    print(f"  {result['draft_response'][:200]}...")
    print()

    return result


def list_pending():
    """List all tickets waiting for approval."""
    print("=" * 60)
    print("STEP 2: List pending tickets")
    print("=" * 60)

    response = httpx.get(f"{BASE_URL}/tickets?status=pending_approval")
    result = response.json()

    print(f"\n  {result['count']} ticket(s) pending approval:")
    for t in result["tickets"]:
        print(f"    {t['ticket_id']} | {t['customer_name']} | {t['category']} | {t['priority']}")
    print()

    return result


def approve(ticket_id: str, edit: bool = False):
    """Approve a ticket, optionally with edits."""
    print("=" * 60)
    action = "EDIT and approve" if edit else "Approve as-is"
    print(f"STEP 3: {action} ticket {ticket_id}")
    print("=" * 60)

    body = {"reviewer": "jay_gujarathi"}

    if edit:
        body["edited_response"] = (
            "Hi Sarah, I apologize for the repeated billing issues. "
            "I've confirmed the duplicate charge of $29.99 on your June bill "
            "and have processed an immediate refund. I've also applied a "
            "complimentary month of service. Our billing team is investigating "
            "the root cause. — Jay"
        )
        body["note"] = "Shortened the response and added personal sign-off"

    response = httpx.post(f"{BASE_URL}/tickets/{ticket_id}/approve", json=body)
    result = response.json()

    print(f"\n  Status:         {result['status']}")
    print(f"  Reviewed by:    {result['reviewed_by']}")
    if result.get("review_note"):
        print(f"  Note:           {result['review_note']}")
    print(f"\n  Final response:")
    print(f"  {result['final_response'][:300]}")
    print()


def reject(ticket_id: str):
    """Reject a ticket."""
    print("=" * 60)
    print(f"STEP 3: Reject ticket {ticket_id}")
    print("=" * 60)

    response = httpx.post(
        f"{BASE_URL}/tickets/{ticket_id}/reject",
        json={
            "reviewer": "jay_gujarathi",
            "reason": "Response needs more specific refund details",
        },
    )
    result = response.json()

    print(f"\n  Status:      {result['status']}")
    print(f"  Reviewed by: {result['reviewed_by']}")
    print(f"  Reason:      {result['review_note']}")
    print()


if __name__ == "__main__":
    # --- Full flow: submit → review → approve with edits ---

    # Step 1: Submit a ticket (agents run, draft queued)
    result = submit_ticket(
        "Sarah Johnson",
        "CUST-001",
        "I've been charged TWICE for my subscription this month! "
        "This is the third time this has happened. I want a refund.",
    )

    ticket_id = result["ticket_id"]

    # Step 2: List pending tickets (what the reviewer sees)
    list_pending()

    # Step 3: Approve with edits (reviewer modifies the draft)
    approve(ticket_id, edit=True)