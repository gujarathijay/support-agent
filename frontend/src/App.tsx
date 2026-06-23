import { useState, useEffect } from "react";
import type { Ticket, TicketRequest } from "./types";
import { submitTicket, getTickets, approveTicket, rejectTicket } from "./api";
import "./App.css";

type View = "submit" | "queue" | "review";

export default function App() {
  const [view, setView] = useState<View>("submit");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (view === "queue") loadTickets();
  }, [view]);

  async function loadTickets() {
    try {
      const all = await getTickets();
      setTickets(all);
    } catch {
      setMessage("Failed to load tickets");
    }
  }

  function openReview(ticket: Ticket) {
    setSelectedTicket(ticket);
    setView("review");
  }

  return (
    <div className="app">
      <header>
        <h1>Sentinel</h1>
        <p className="subtitle">Support Resolution Agent</p>
        <nav>
          <button
            className={view === "submit" ? "active" : ""}
            onClick={() => setView("submit")}
          >
            Submit Ticket
          </button>
          <button
            className={view === "queue" ? "active" : ""}
            onClick={() => setView("queue")}
          >
            Review Queue
          </button>
        </nav>
      </header>

      <main>
        {message && (
          <div className="message" onClick={() => setMessage("")}>
            {message}
          </div>
        )}

        {view === "submit" && (
          <SubmitForm
            loading={loading}
            onSubmit={async (req) => {
              setLoading(true);
              setMessage("");
              try {
                const result = await submitTicket(req);
                setMessage(
                  `Ticket ${result.ticket_id} created — ${result.category}/${result.priority}. Awaiting review.`
                );
              } catch (e: any) {
                setMessage(`Error: ${e.message}`);
              }
              setLoading(false);
            }}
          />
        )}

        {view === "queue" && (
          <TicketQueue tickets={tickets} onSelect={openReview} onRefresh={loadTickets} />
        )}

        {view === "review" && selectedTicket && (
          <ReviewPanel
            ticket={selectedTicket}
            onDone={(msg) => {
              setMessage(msg);
              setView("queue");
              setSelectedTicket(null);
            }}
          />
        )}
      </main>
    </div>
  );
}

/* Submit Form */

function SubmitForm({
  loading,
  onSubmit,
}: {
  loading: boolean;
  onSubmit: (req: TicketRequest) => void;
}) {
  const [name, setName] = useState("Sarah Johnson");
  const [custId, setCustId] = useState("CUST-001");
  const [msg, setMsg] = useState("");

  return (
    <section className="form-section">
      <h2>Submit a Support Ticket</h2>
      <div className="form">
        <label>
          Customer Name
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          Customer ID
          <input value={custId} onChange={(e) => setCustId(e.target.value)} />
        </label>
        <label>
          Message
          <textarea
            rows={4}
            value={msg}
            onChange={(e) => setMsg(e.target.value)}
            placeholder="Describe the customer's issue..."
          />
        </label>
        <button
          className="primary"
          disabled={loading || !msg.trim()}
          onClick={() =>
            onSubmit({ customer_name: name, customer_id: custId, message: msg })
          }
        >
          {loading ? "Processing... (30-60s)" : "Submit Ticket"}
        </button>
      </div>
    </section>
  );
}

/* Ticket Queue */

function TicketQueue({
  tickets,
  onSelect,
  onRefresh,
}: {
  tickets: Ticket[];
  onSelect: (t: Ticket) => void;
  onRefresh: () => void;
}) {
  const pending = tickets.filter((t) => t.status === "pending_approval");
  const reviewed = tickets.filter((t) => t.status !== "pending_approval");

  return (
    <section>
      <div className="queue-header">
        <h2>Pending Review ({pending.length})</h2>
        <button onClick={onRefresh}>Refresh</button>
      </div>

      {pending.length === 0 && <p className="empty">No tickets pending review.</p>}

      {pending.map((t) => (
        <div key={t.ticket_id} className="ticket-card" onClick={() => onSelect(t)}>
          <div className="ticket-row">
            <strong>{t.ticket_id}</strong>
            <span className={`badge ${t.priority}`}>{t.priority}</span>
            <span className={`badge ${t.sentiment}`}>{t.sentiment}</span>
            <span className="badge">{t.category}</span>
          </div>
          <div className="ticket-row">
            <span>{t.customer_name} ({t.customer_id})</span>
            <span className="date">{new Date(t.created_at).toLocaleString()}</span>
          </div>
          <p className="ticket-summary">{t.summary}</p>
        </div>
      ))}

      {reviewed.length > 0 && (
        <>
          <h2 className="mt">Reviewed ({reviewed.length})</h2>
          {reviewed.map((t) => (
            <div key={t.ticket_id} className="ticket-card reviewed" onClick={() => onSelect(t)}>
              <div className="ticket-row">
                <strong>{t.ticket_id}</strong>
                <span className={`badge ${t.status}`}>{t.status}</span>
                <span className="badge">{t.category}</span>
              </div>
              <div className="ticket-row">
                <span>{t.customer_name}</span>
                {t.reviewed_by && <span>Reviewed by: {t.reviewed_by}</span>}
              </div>
            </div>
          ))}
        </>
      )}
    </section>
  );
}

/* Review Panel */

function ReviewPanel({
  ticket,
  onDone,
}: {
  ticket: Ticket;
  onDone: (msg: string) => void;
}) {
  const [editedResponse, setEditedResponse] = useState(ticket.draft_response);
  const [rejectReason, setRejectReason] = useState("");
  const [loading, setLoading] = useState(false);
  const isEdited = editedResponse !== ticket.draft_response;

  async function handleApprove() {
    setLoading(true);
    try {
      await approveTicket(
        ticket.ticket_id,
        "reviewer",
        isEdited ? editedResponse : undefined
      );
      onDone(`${ticket.ticket_id} ${isEdited ? "edited and approved" : "approved"}.`);
    } catch (e: any) {
      onDone(`Error: ${e.message}`);
    }
    setLoading(false);
  }

  async function handleReject() {
    if (!rejectReason.trim()) return;
    setLoading(true);
    try {
      await rejectTicket(ticket.ticket_id, "reviewer", rejectReason);
      onDone(`${ticket.ticket_id} rejected.`);
    } catch (e: any) {
      onDone(`Error: ${e.message}`);
    }
    setLoading(false);
  }

  return (
    <section className="review">
      <h2>Review: {ticket.ticket_id}</h2>

      <div className="detail-grid">
        <div className="detail-block">
          <h3>Customer</h3>
          <p>{ticket.customer_name} ({ticket.customer_id})</p>
          <p className="customer-message">{ticket.message}</p>
        </div>

        <div className="detail-block">
          <h3>Triage</h3>
          <div className="badge-row">
            <span className={`badge ${ticket.priority}`}>{ticket.priority}</span>
            <span className={`badge ${ticket.sentiment}`}>{ticket.sentiment}</span>
            <span className="badge">{ticket.category}</span>
          </div>
          <p>{ticket.summary}</p>
        </div>
      </div>

      <div className="detail-block">
        <h3>Guardrails</h3>
        <p className={ticket.guardrail_passed ? "pass" : "fail"}>
          {ticket.guardrail_passed ? "✓ Passed" : "✗ Failed"} — {ticket.guardrail_summary}
        </p>
        {ticket.guardrail_violations.map((v, i) => (
          <p key={i} className="violation">
            [{v.severity.toUpperCase()}] {v.message}
          </p>
        ))}
      </div>

      <div className="detail-block">
        <h3>Tools Called</h3>
        <p>{(ticket.tools_called || []).join(", ") || "None recorded"}</p>
      </div>

      <div className="detail-block">
        <h3>Draft Response {isEdited && <span className="edited-tag">(edited)</span>}</h3>
        {ticket.status === "pending_approval" ? (
          <textarea
            rows={10}
            value={editedResponse}
            onChange={(e) => setEditedResponse(e.target.value)}
          />
        ) : (
          <p className="response-text">{ticket.final_response || ticket.draft_response}</p>
        )}
      </div>

      {ticket.status === "pending_approval" && (
        <div className="actions">
          <button className="primary" onClick={handleApprove} disabled={loading}>
            {isEdited ? "Approve with Edits" : "Approve"}
          </button>
          <div className="reject-row">
            <input
              placeholder="Reason for rejection..."
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
            />
            <button
              className="danger"
              onClick={handleReject}
              disabled={loading || !rejectReason.trim()}
            >
              Reject
            </button>
          </div>
        </div>
      )}

      {ticket.status !== "pending_approval" && (
        <div className="detail-block">
          <h3>Review Decision</h3>
          <p>
            Status: <strong>{ticket.status}</strong>
            {ticket.reviewed_by && <> by {ticket.reviewed_by}</>}
          </p>
          {ticket.review_note && <p>Note: {ticket.review_note}</p>}
        </div>
      )}
    </section>
  );
}