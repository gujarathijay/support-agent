export interface Ticket {
  ticket_id: string;
  status: string;
  created_at: string;
  updated_at: string;
  customer_name: string;
  customer_id: string;
  message: string;
  category: string;
  priority: string;
  sentiment: string;
  summary: string;
  triage_reasoning: string;
  research_findings: string;
  draft_response: string;
  tools_called: string[];
  guardrail_passed: boolean;
  guardrail_violations: Violation[];
  guardrail_summary: string;
  reviewed_by: string | null;
  review_note: string | null;
  final_response: string | null;
}

export interface Violation {
  type: string;
  message: string;
  severity: string;
}

export interface TicketRequest {
  customer_name: string;
  customer_id: string;
  message: string;
}