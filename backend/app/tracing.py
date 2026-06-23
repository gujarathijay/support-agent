"""
Tracing module — structured observability for the agent workflow.

Every workflow run creates a Trace containing multiple Spans:
  - Trace: the entire run (one per ticket)
  - Span: a single step (one per agent node, one per tool call)

Each span records:
  - name: what step this is ("triage", "research", "resolution")
  - input: what the step received
  - output: what the step returned
  - duration_ms: how long it took
  - metadata: extra context (model used, tokens, tool calls)

Traces are stored in memory and accessible via API.
When Braintrust is configured, they're also sent to the dashboard.
"""

import time
import uuid
import json
from datetime import datetime
from typing import Any
from app.config import settings


# In-memory trace storage (Phase 7's SQLite could store these too)
_traces: dict[str, dict] = {}


class Span:
    """A single step in a workflow trace."""

    def __init__(self, name: str, trace_id: str, input_data: Any = None):
        self.span_id = uuid.uuid4().hex[:8]
        self.trace_id = trace_id
        self.name = name
        self.input_data = _safe_truncate(input_data)
        self.output_data = None
        self.start_time = time.time()
        self.end_time = None
        self.duration_ms = None
        self.metadata = {}
        self.status = "running"

    def end(self, output_data: Any = None, metadata: dict = None):
        """Mark span as complete."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000)
        self.output_data = _safe_truncate(output_data)
        if metadata:
            self.metadata.update(metadata)
        self.status = "completed"

    def error(self, error_msg: str):
        """Mark span as failed."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000)
        self.status = "error"
        self.metadata["error"] = error_msg

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "name": self.name,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "input": self.input_data,
            "output": self.output_data,
            "metadata": self.metadata,
        }


class Trace:
    """A complete workflow execution trace."""

    def __init__(self, ticket_id: str = "", customer_name: str = ""):
        self.trace_id = uuid.uuid4().hex[:12]
        self.ticket_id = ticket_id
        self.customer_name = customer_name
        self.spans: list[Span] = []
        self.start_time = time.time()
        self.end_time = None
        self.total_duration_ms = None
        self.created_at = datetime.now().isoformat()

    def start_span(self, name: str, input_data: Any = None) -> Span:
        """Start a new span within this trace."""
        span = Span(name=name, trace_id=self.trace_id, input_data=input_data)
        self.spans.append(span)
        return span

    def end(self):
        """Mark the trace as complete."""
        self.end_time = time.time()
        self.total_duration_ms = round((self.end_time - self.start_time) * 1000)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "ticket_id": self.ticket_id,
            "customer_name": self.customer_name,
            "created_at": self.created_at,
            "total_duration_ms": self.total_duration_ms,
            "spans": [s.to_dict() for s in self.spans],
            "summary": {
                "total_spans": len(self.spans),
                "total_duration_s": round(self.total_duration_ms / 1000, 1) if self.total_duration_ms else None,
                "span_durations": {
                    s.name: f"{s.duration_ms}ms" for s in self.spans if s.duration_ms
                },
            },
        }


# ---------------------------------------------------------------------------
# Trace storage
# ---------------------------------------------------------------------------

def store_trace(trace: Trace):
    """Store a completed trace."""
    trace.end()
    _traces[trace.trace_id] = trace.to_dict()
    print(f"  [Trace] Stored trace {trace.trace_id} ({trace.total_duration_ms}ms, {len(trace.spans)} spans)")


def get_trace(trace_id: str) -> dict | None:
    return _traces.get(trace_id)


def list_traces(limit: int = 20) -> list[dict]:
    traces = sorted(_traces.values(), key=lambda t: t["created_at"], reverse=True)
    return traces[:limit]


def _safe_truncate(data: Any, max_len: int = 500) -> Any:
    """Truncate large data for storage. Full data stays in the workflow."""
    if data is None:
        return None
    if isinstance(data, str):
        return data[:max_len] + "..." if len(data) > max_len else data
    if isinstance(data, dict):
        return {k: _safe_truncate(v, max_len) for k, v in data.items()}
    return str(data)[:max_len]