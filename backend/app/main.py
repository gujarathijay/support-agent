"""
FastAPI application — the entry point of our backend.

Endpoints:
  GET  /health                  → health check
  POST /triage                  → Phase 1: single-agent triage
  POST /resolve                 → full workflow → pending approval
  GET  /tickets                 → list tickets (filter by status)
  GET  /tickets/{id}            → get a single ticket
  POST /tickets/{id}/approve    → approve a pending ticket
  POST /tickets/{id}/reject     → reject a pending ticket
  GET  /traces                  → list recent traces
  GET  /traces/{id}             → get a single trace
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import (
    TicketRequest, TriageResult, TriageResponse,
    WorkflowResponse, ApproveRequest, RejectRequest,
)
from app.llm import triage_ticket
from app.graph import support_graph
from app.memory import store_memory
from app.ticket_store import (
    store_ticket, get_ticket, list_tickets,
    approve_ticket, reject_ticket,
)
from app.tracing import Trace, store_trace, get_trace, list_traces
import time


app = FastAPI(
    title="Support Resolution Agent",
    description="AI-powered multi-agent system for customer support triage and resolution",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Phase 1: Single-agent triage
# ---------------------------------------------------------------------------

@app.post("/triage", response_model=TriageResponse)
async def triage_endpoint(ticket: TicketRequest):
    try:
        triage_result: TriageResult = await triage_ticket(
            customer_name=ticket.customer_name,
            message=ticket.message,
        )
        return TriageResponse(ticket=ticket, triage=triage_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Triage failed: {str(e)}")


# ---------------------------------------------------------------------------
# Full workflow with tracing
# ---------------------------------------------------------------------------

@app.post("/resolve", response_model=WorkflowResponse)
async def resolve_endpoint(ticket: TicketRequest):
    """Run the full workflow with tracing."""
    try:
        # Start trace
        trace = Trace(customer_name=ticket.customer_name)

        initial_state = {
            "customer_name": ticket.customer_name,
            "customer_id": ticket.customer_id,
            "message": ticket.message,
        }

        # Run workflow with a top-level span
        workflow_span = trace.start_span("workflow", input_data={
            "customer_name": ticket.customer_name,
            "customer_id": ticket.customer_id,
            "message": ticket.message[:200],
        })

        start_time = time.time()
        print(f"\n  [Workflow] Starting for {ticket.customer_name} ({ticket.customer_id})")

        final_state = await support_graph.ainvoke(initial_state)

        elapsed = time.time() - start_time

        workflow_span.end(
            output_data={
                "category": final_state.get("category"),
                "priority": final_state.get("priority"),
                "sentiment": final_state.get("sentiment"),
                "guardrail_passed": final_state.get("guardrail_passed"),
                "tools_called": final_state.get("tools_called", []),
            },
            metadata={
                "duration_s": round(elapsed, 1),
                "model": "claude-sonnet-4-5",
                "tools_called_count": len(final_state.get("tools_called", [])),
            },
        )

        print(f"  [Workflow] Completed in {elapsed:.1f}s")

        # Store memory
        try:
            memory_id = store_memory(
                customer_id=ticket.customer_id,
                customer_name=ticket.customer_name,
                category=final_state.get("category", "general"),
                priority=final_state.get("priority", "medium"),
                summary=final_state.get("summary", "No summary"),
                resolution=final_state.get("draft_response", "No resolution")[:500],
            )
            print(f"  [Memory] Stored as {memory_id}")
        except Exception as mem_err:
            print(f"  [Memory] Warning: {mem_err}")

        # Store ticket for approval
        ticket_id = store_ticket(final_state)
        print(f"  [Approval] Queued as {ticket_id}")

        # Store trace
        trace.ticket_id = ticket_id
        store_trace(trace)

        return WorkflowResponse(ticket_id=ticket_id, status="pending_approval", **final_state)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


# ---------------------------------------------------------------------------
# Ticket approval
# ---------------------------------------------------------------------------

@app.get("/tickets")
async def list_tickets_endpoint(status: str | None = None):
    tickets = list_tickets(status)
    return {"tickets": tickets, "count": len(tickets)}


@app.get("/tickets/{ticket_id}")
async def get_ticket_endpoint(ticket_id: str):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@app.post("/tickets/{ticket_id}/approve")
async def approve_ticket_endpoint(ticket_id: str, request: ApproveRequest):
    result = approve_ticket(
        ticket_id=ticket_id,
        reviewer=request.reviewer,
        edited_response=request.edited_response,
        note=request.note,
    )
    if not result:
        raise HTTPException(status_code=400, detail=f"Ticket {ticket_id} not found or not pending")
    action = "edited and approved" if request.edited_response else "approved"
    print(f"  [Approval] {ticket_id} {action} by {request.reviewer}")
    return result


@app.post("/tickets/{ticket_id}/reject")
async def reject_ticket_endpoint(ticket_id: str, request: RejectRequest):
    result = reject_ticket(
        ticket_id=ticket_id,
        reviewer=request.reviewer,
        reason=request.reason,
    )
    if not result:
        raise HTTPException(status_code=400, detail=f"Ticket {ticket_id} not found or not pending")
    print(f"  [Approval] {ticket_id} rejected by {request.reviewer}: {request.reason}")
    return result


# ---------------------------------------------------------------------------
# Tracing endpoints
# ---------------------------------------------------------------------------

@app.get("/traces")
async def list_traces_endpoint(limit: int = 20):
    """List recent workflow traces for observability."""
    traces = list_traces(limit)
    return {"traces": traces, "count": len(traces)}


@app.get("/traces/{trace_id}")
async def get_trace_endpoint(trace_id: str):
    """Get a single trace with all spans."""
    trace = get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
    return trace


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)