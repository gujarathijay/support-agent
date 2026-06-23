"""
Mock data for the support resolution agent.

In production, this data would live in a real database (Postgres, etc.)
and be accessed through an ORM or API. We use dictionaries here so you
can see the actual data the tools return — no database setup needed.

This gets replaced with real database queries in Phase 7 (persistence).
"""

# ---------------------------------------------------------------------------
# Customer orders — simulates an orders table
# ---------------------------------------------------------------------------

ORDERS = {
    "CUST-001": {
        "customer_name": "Sarah Johnson",
        "email": "sarah.j@email.com",
        "plan": "Pro Monthly",
        "monthly_price": 29.99,
        "orders": [
            {
                "order_id": "ORD-1001",
                "date": "2025-06-01",
                "amount": 29.99,
                "status": "completed",
                "description": "Pro Monthly - June",
            },
            {
                "order_id": "ORD-1002",
                "date": "2025-06-01",
                "amount": 29.99,
                "status": "completed",
                "description": "Pro Monthly - June (DUPLICATE)",
            },
            {
                "order_id": "ORD-0998",
                "date": "2025-05-01",
                "amount": 29.99,
                "status": "completed",
                "description": "Pro Monthly - May",
            },
            {
                "order_id": "ORD-0999",
                "date": "2025-05-01",
                "amount": 29.99,
                "status": "refunded",
                "description": "Pro Monthly - May (DUPLICATE - refunded)",
            },
        ],
    },
    "CUST-002": {
        "customer_name": "Mike Chen",
        "email": "mike.chen@email.com",
        "plan": "Basic Annual",
        "monthly_price": 9.99,
        "orders": [
            {
                "order_id": "ORD-0950",
                "date": "2025-01-15",
                "amount": 119.88,
                "status": "completed",
                "description": "Basic Annual Plan",
            },
        ],
    },
    "CUST-003": {
        "customer_name": "Alex Rivera",
        "email": "alex.r@techcorp.com",
        "plan": "Enterprise",
        "monthly_price": 199.99,
        "orders": [
            {
                "order_id": "ORD-1010",
                "date": "2025-06-01",
                "amount": 199.99,
                "status": "completed",
                "description": "Enterprise - June",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Knowledge base — simulates a searchable help center
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE = [
    {
        "id": "KB-001",
        "title": "Refund Policy",
        "category": "billing",
        "content": (
            "Refund policy: Customers are entitled to a full refund for "
            "duplicate charges within 30 days. Refunds are processed within "
            "5-7 business days. For recurring duplicate charges (2+ occurrences), "
            "escalate to billing team lead and offer one month free credit "
            "as goodwill gesture. Maximum refund authority for support agents: "
            "$500. Amounts above $500 require manager approval."
        ),
    },
    {
        "id": "KB-002",
        "title": "Data Export Guide",
        "category": "product",
        "content": (
            "Data export: Users can export their data in CSV, JSON, or PDF "
            "format. Navigate to Settings > Data > Export. Select the date "
            "range and format. Large exports (>10,000 rows) are processed "
            "in the background and emailed to the user. Export is available "
            "on all plans including Basic."
        ),
    },
    {
        "id": "KB-003",
        "title": "Service Outage Procedures",
        "category": "technical",
        "content": (
            "During service outages: 1) Check status.example.com for known "
            "issues. 2) If the issue is confirmed, provide the customer with "
            "the incident ID and estimated resolution time. 3) For Enterprise "
            "customers, offer a direct escalation to the on-call engineer. "
            "4) If outage exceeds 4 hours, eligible customers receive SLA "
            "credit automatically. Enterprise SLA: 99.9% uptime guarantee."
        ),
    },
    {
        "id": "KB-004",
        "title": "Account Security",
        "category": "account",
        "content": (
            "Account security: If a customer suspects unauthorized access, "
            "immediately trigger a password reset and enable 2FA. Review "
            "the last 30 days of login history. If suspicious activity is "
            "confirmed, escalate to the security team and freeze the account "
            "pending investigation. Notify the customer within 24 hours."
        ),
    },
    {
        "id": "KB-005",
        "title": "Subscription Cancellation",
        "category": "billing",
        "content": (
            "Cancellation policy: Customers can cancel anytime. Annual plans "
            "are prorated for remaining months. Monthly plans end at the "
            "current billing period. Retention offer: 50% off for 3 months "
            "can be offered to customers who have been subscribed for 6+ "
            "months. All cancellations require a brief reason survey."
        ),
    },
    {
        "id": "KB-006",
        "title": "Dashboard Error Troubleshooting",
        "category": "technical",
        "content": (
            "For 500 errors on dashboard: 1) Ask customer to clear browser "
            "cache and try incognito mode. 2) Check if the issue is specific "
            "to one browser. 3) If issue persists across browsers, collect "
            "the error timestamp and customer ID for engineering. 4) For "
            "Enterprise customers, the dedicated support channel can "
            "escalate directly to the platform team."
        ),
    },
]