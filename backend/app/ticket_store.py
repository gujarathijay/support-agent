"""
Ticket store — now backed by SQLite.

Same interface as before (store, get, list, approve, reject) but
data now persists to support_agent.db. Restart the server and
your tickets are still there.

This module is a thin wrapper around database.py. The rest of the
app imports from here and doesn't know or care whether the storage
is a dict, SQLite, or Postgres. That's the point of having a
separate storage layer — you can swap the backend without changing
any other code.
"""

import uuid
from app.database import (
    insert_ticket,
    get_ticket_by_id,
    get_tickets,
    update_ticket_status,
)


def store_ticket(workflow_result: dict) -> str:
    """Store a completed workflow result as a pending ticket.
    Returns a ticket ID."""
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    insert_ticket(ticket_id, workflow_result)
    return ticket_id


def get_ticket(ticket_id: str) -> dict | None:
    """Get a ticket by ID."""
    return get_ticket_by_id(ticket_id)


def list_tickets(status: str | None = None) -> list[dict]:
    """List all tickets, optionally filtered by status."""
    return get_tickets(status)


def approve_ticket(
    ticket_id: str,
    reviewer: str = "human_reviewer",
    edited_response: str | None = None,
    note: str | None = None,
) -> dict | None:
    """Approve a pending ticket."""
    # Get the current ticket to determine final_response
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        return None

    if edited_response:
        status = "edited"
        final = edited_response
    else:
        status = "approved"
        final = ticket["draft_response"]

    return update_ticket_status(
        ticket_id=ticket_id,
        status=status,
        reviewer=reviewer,
        review_note=note,
        final_response=final,
    )


def reject_ticket(
    ticket_id: str,
    reviewer: str = "human_reviewer",
    reason: str = "No reason provided",
) -> dict | None:
    """Reject a pending ticket."""
    return update_ticket_status(
        ticket_id=ticket_id,
        status="rejected",
        reviewer=reviewer,
        review_note=reason,
    )