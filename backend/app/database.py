"""
Database module — SQLite persistence for tickets.

This replaces the in-memory dictionary with a real database.
Data is stored in support_agent.db in the backend directory.

Design decisions:
  1. We use plain sqlite3 (built into Python) — no ORM, no extra
     dependencies. You see the actual SQL, which is what runs in
     production databases too.
  2. We use parameterized queries (? placeholders) to prevent SQL
     injection — never put user input directly into SQL strings.
  3. We store guardrail_violations as JSON text in one column.
     In Postgres you'd use a JSONB column; in SQLite, a TEXT
     column with json.dumps/loads works fine.
  4. The database file persists across server restarts. Delete
     support_agent.db to start fresh.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path


# Database file location — same directory as the backend
DB_PATH = Path(__file__).parent.parent / "support_agent.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row_factory set for dict-like access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # access columns by name, not index
    conn.execute("PRAGMA journal_mode=WAL")  # better concurrent read performance
    return conn


def init_db():
    """Create tables if they don't exist.

    Called once at startup. Safe to call multiple times —
    'IF NOT EXISTS' means it's a no-op if tables already exist.
    """
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id       TEXT PRIMARY KEY,
            status          TEXT NOT NULL DEFAULT 'pending_approval',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL,

            -- Customer info
            customer_name   TEXT NOT NULL,
            customer_id     TEXT NOT NULL,
            message         TEXT NOT NULL,

            -- Triage results
            category        TEXT,
            priority        TEXT,
            sentiment       TEXT,
            summary         TEXT,
            triage_reasoning TEXT,

            -- Research results
            research_findings TEXT,

            -- Resolution
            draft_response  TEXT,

            -- Guardrails
            guardrail_passed  INTEGER,
            guardrail_violations TEXT,
            guardrail_summary TEXT,

            -- Approval
            reviewed_by     TEXT,
            review_note     TEXT,
            final_response  TEXT
        )
    """)

    # Index on status — we frequently query by status
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)
    """)

    # Index on customer_id — for looking up customer history
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id)
    """)

    conn.commit()
    conn.close()
    print(f"  [Database] Initialized at {DB_PATH}")


def insert_ticket(ticket_id: str, data: dict):
    """Insert a new ticket into the database."""
    conn = get_connection()
    now = datetime.now().isoformat()

    conn.execute("""
        INSERT INTO tickets (
            ticket_id, status, created_at, updated_at,
            customer_name, customer_id, message,
            category, priority, sentiment, summary, triage_reasoning,
            research_findings, draft_response,
            guardrail_passed, guardrail_violations, guardrail_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket_id, "pending_approval", now, now,
        data.get("customer_name", ""),
        data.get("customer_id", ""),
        data.get("message", ""),
        data.get("category"),
        data.get("priority"),
        data.get("sentiment"),
        data.get("summary"),
        data.get("triage_reasoning"),
        data.get("research_findings"),
        data.get("draft_response"),
        1 if data.get("guardrail_passed") else 0,
        json.dumps(data.get("guardrail_violations", [])),
        data.get("guardrail_summary"),
    ))

    conn.commit()
    conn.close()


def get_ticket_by_id(ticket_id: str) -> dict | None:
    """Get a single ticket by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    conn.close()

    if row:
        return _row_to_dict(row)
    return None


def get_tickets(status: str | None = None) -> list[dict]:
    """Get all tickets, optionally filtered by status."""
    conn = get_connection()

    if status:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tickets ORDER BY created_at DESC"
        ).fetchall()

    conn.close()
    return [_row_to_dict(row) for row in rows]


def update_ticket_status(
    ticket_id: str,
    status: str,
    reviewer: str | None = None,
    review_note: str | None = None,
    final_response: str | None = None,
) -> dict | None:
    """Update a ticket's status and approval details."""
    conn = get_connection()
    now = datetime.now().isoformat()

    conn.execute("""
        UPDATE tickets
        SET status = ?, updated_at = ?, reviewed_by = ?,
            review_note = ?, final_response = ?
        WHERE ticket_id = ? AND status = 'pending_approval'
    """, (status, now, reviewer, review_note, final_response, ticket_id))

    if conn.total_changes == 0:
        conn.close()
        return None

    conn.commit()

    # Fetch and return the updated ticket
    row = conn.execute(
        "SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()
    conn.close()

    return _row_to_dict(row) if row else None


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a database row to a dictionary.

    Handles type conversions:
    - guardrail_passed: INTEGER → bool
    - guardrail_violations: JSON string → list
    """
    d = dict(row)

    # Convert integer back to boolean
    d["guardrail_passed"] = bool(d.get("guardrail_passed", 0))

    # Parse JSON violations
    violations = d.get("guardrail_violations", "[]")
    try:
        d["guardrail_violations"] = json.loads(violations) if violations else []
    except json.JSONDecodeError:
        d["guardrail_violations"] = []

    return d


# Initialize the database when this module is imported
init_db()