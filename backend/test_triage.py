"""
Test script for the triage endpoint.

Run this AFTER starting the server:
  1. Start server:  cd backend && uvicorn app.main:app --reload
  2. Run tests:     python test_triage.py

This sends sample support tickets to your API and prints the
structured triage results. It's a quick smoke test, not a
replacement for proper evals (those come in Phase 9 with Braintrust).
"""

import httpx
import json

BASE_URL = "http://localhost:8000"

TIMEOUT=60

def test_health():
    """Test that the server is running."""
    response = httpx.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    print(f"Health check: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()


def test_triage(customer_name: str, message: str):
    """Send a ticket and print the triage result."""
    print(f"--- Ticket from: {customer_name} ---")
    print(f"Message: {message[:80]}...")
    print()

    response = httpx.post(
    f"{BASE_URL}/triage",
    json={
        "customer_name": customer_name,
        "message": message,
        "customer_id": "CUST-001",
    },
    timeout=TIMEOUT,
    )

    if response.status_code == 200:
        result = response.json()
        triage = result["triage"]
        print(f"  Category:  {triage['category']}")
        print(f"  Priority:  {triage['priority']}")
        print(f"  Sentiment: {triage['sentiment']}")
        print(f"  Summary:   {triage['summary']}")
        print(f"  Reasoning: {triage['reasoning']}")
    else:
        print(f"  ERROR {response.status_code}: {response.text}")
    print()


if __name__ == "__main__":
    # Test 1: Health check
    test_health()

    # Test 2: Angry customer with billing issue (should be high priority)
    test_triage(
        "Sarah Johnson",
        "I've been charged TWICE for my subscription this month! "
        "This is the third time this has happened. I want a refund "
        "immediately or I'm canceling my account and filing a dispute "
        "with my credit card company."
    )

    # Test 3: Calm customer with a question (should be low priority)
    test_triage(
        "Mike Chen",
        "Hi there, I was wondering if it's possible to export my "
        "data as a CSV file? I'd like to use it in a spreadsheet. "
        "No rush, just curious. Thanks!"
    )

    # Test 4: Urgent technical issue (should be urgent priority)
    test_triage(
        "Alex Rivera",
        "Our entire team's dashboard has been showing a 500 error "
        "for the past 2 hours. None of us can access any data. "
        "We have a client presentation in 30 minutes and we're "
        "completely blocked. Please help ASAP!"
    )