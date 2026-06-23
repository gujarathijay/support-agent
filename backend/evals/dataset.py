"""
Eval dataset — test cases with expected outputs.

Each test case has:
  - input: what we send to the agent (the ticket)
  - expected: what the correct output should be
  
These are human-labeled ground truth examples. When we run evals,
we compare the agent's output against these expected values.

A good eval dataset:
  1. Covers all categories (billing, technical, account, product, general)
  2. Covers all priorities (low, medium, high, urgent)
  3. Covers all sentiments (angry, frustrated, neutral, positive)
  4. Includes edge cases (ambiguous tickets, multi-issue tickets)
  5. Has at least 10-20 examples per category for statistical significance

We start with 8 examples to demonstrate the concept. In production,
you'd have 50-200+ labeled examples.
"""

EVAL_DATASET = [
    {
        "input": {
            "customer_name": "Sarah Johnson",
            "customer_id": "CUST-001",
            "message": (
                "I've been charged TWICE for my subscription this month! "
                "This is the third time this has happened. I want a refund "
                "immediately or I'm canceling my account."
            ),
        },
        "expected": {
            "category": "billing",
            "priority": "high",
            "sentiment": "angry",
        },
    },
    {
        "input": {
            "customer_name": "Mike Chen",
            "customer_id": "CUST-002",
            "message": (
                "Hi there, I was wondering if it's possible to export my "
                "data as a CSV file? I'd like to use it in a spreadsheet. "
                "No rush, just curious. Thanks!"
            ),
        },
        "expected": {
            "category": "product",
            "priority": "low",
            "sentiment": "positive",
        },
    },
    {
        "input": {
            "customer_name": "Alex Rivera",
            "customer_id": "CUST-003",
            "message": (
                "Our entire team's dashboard has been showing a 500 error "
                "for the past 2 hours. None of us can access any data. "
                "We have a client presentation in 30 minutes and we're "
                "completely blocked. Please help ASAP!"
            ),
        },
        "expected": {
            "category": "technical",
            "priority": "urgent",
            "sentiment": "frustrated",
        },
    },
    {
        "input": {
            "customer_name": "Lisa Park",
            "customer_id": "CUST-004",
            "message": (
                "I think someone else has accessed my account. I'm seeing "
                "login notifications from a device I don't recognize. "
                "Please help me secure my account right away."
            ),
        },
        "expected": {
            "category": "account",
            "priority": "urgent",
            "sentiment": "frustrated",
        },
    },
    {
        "input": {
            "customer_name": "Tom Wilson",
            "customer_id": "CUST-005",
            "message": (
                "Love your product! Just wanted to suggest adding a dark "
                "mode option. Would make late-night work sessions easier. "
                "Keep up the great work!"
            ),
        },
        "expected": {
            "category": "product",
            "priority": "low",
            "sentiment": "positive",
        },
    },
    {
        "input": {
            "customer_name": "Emma Davis",
            "customer_id": "CUST-006",
            "message": (
                "I've been trying to cancel my subscription for two weeks "
                "now but the cancel button doesn't work. I keep getting "
                "charged. This is really frustrating."
            ),
        },
        "expected": {
            "category": "billing",
            "priority": "high",
            "sentiment": "frustrated",
        },
    },
    {
        "input": {
            "customer_name": "James Lee",
            "customer_id": "CUST-007",
            "message": (
                "How do I change my password? I can't find the option "
                "in settings."
            ),
        },
        "expected": {
            "category": "account",
            "priority": "low",
            "sentiment": "neutral",
        },
    },
    {
        "input": {
            "customer_name": "Nina Patel",
            "customer_id": "CUST-008",
            "message": (
                "The search feature has been extremely slow for the past "
                "week. It takes 30+ seconds to return results. This is "
                "making it very hard to do my job."
            ),
        },
        "expected": {
            "category": "technical",
            "priority": "medium",
            "sentiment": "frustrated",
        },
    },
]