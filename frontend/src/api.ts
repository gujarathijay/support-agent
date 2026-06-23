import type { Ticket, TicketRequest } from "./types";

const BASE = "http://localhost:8000";

export async function submitTicket(req: TicketRequest): Promise<Ticket> {
  const res = await fetch(`${BASE}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getTickets(status?: string): Promise<Ticket[]> {
  const url = status ? `${BASE}/tickets?status=${status}` : `${BASE}/tickets`;
  const res = await fetch(url);
  const data = await res.json();
  return data.tickets;
}

export async function getTicket(id: string): Promise<Ticket> {
  const res = await fetch(`${BASE}/tickets/${id}`);
  if (!res.ok) throw new Error("Ticket not found");
  return res.json();
}

export async function approveTicket(
  id: string,
  reviewer: string,
  editedResponse?: string,
  note?: string
): Promise<Ticket> {
  const res = await fetch(`${BASE}/tickets/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      reviewer,
      edited_response: editedResponse || null,
      note: note || null,
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function rejectTicket(
  id: string,
  reviewer: string,
  reason: string
): Promise<Ticket> {
  const res = await fetch(`${BASE}/tickets/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer, reason }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}